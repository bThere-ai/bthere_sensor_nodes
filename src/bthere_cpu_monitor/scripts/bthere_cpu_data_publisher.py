#!/usr/bin/env python

#renamed from bthere_cpu_monitor.py because of package name conflict
#in the CPUData message import.

from rospy import init_node, loginfo, logerr, logwarn, ROSInterruptException, Publisher, Rate, is_shutdown, get_param, Time
from bthere_cpu_monitor.msg import CPUData
from os import listdir
from platform import uname
from glob import glob
from math import isnan


SUPPORTED_ARCHITECTURES = ["x86_64", "aarch64"] # x86_64, 64 bit arm (raspberry pi)


def get_hwmon_dir(architecture):
    """Gets the path of the hwmon directory for the CPU, depending on architecture."""
    hwmons = listdir("/sys/class/hwmon")
    for hwmon in hwmons:
            name_file = open("/sys/class/hwmon/" + hwmon + "/name")
            name = name_file.read().strip()
            if(name == "coretemp" or name == "cpu_thermal"): 
                # The name file seems to always be "coretemp" on amd64 and cpu_thermal on a raspberry pi 3.
                # This check might not be portable to all systems- more testing and/or research might be necessary.
                name_file.close()
                return "/sys/class/hwmon/" + hwmon
            name_file.close()


def get_cpu_temps(architecture):
    """Gets the available current cpu temperature(s) depending on the system architecture.
    returns: a tuple of type (float, float[]) where the the first element is CPU package (overall) temperature 
        in degrees C, and the second element is a list of per-core CPU temperatures (also deg. C).
        Will return (NaN, []) if an error is encountered.
        If per-core temperatures are not available, the per-core list will be empty.

    note: 
        this function is dependent on the numbering of the files in the directory for the cpu in 
        /sys/class/hwmon/ being consistent, which they may not be.
        The structure seems to be that in /sys/class/hwmon there will be a directory (among others) containing
        a file "name" containing simply "coretemp", with contents such as "temp1_input, temp1_crit, temp1_label,
        temp2_input, temp2_crit, temp2_label", etc. Each of the tempX files corresponds to a temperature sensor
        as labeled by tempX_label as "Package id Y" for the CPU package, "Core Y" for a specific core, etc.
    """
    try:
        package_temp = None
        core_temps = []
        cpu_hwmon_path = get_hwmon_dir(architecture)
        if(architecture == "x86_64"):
            labels = glob(cpu_hwmon_path + "/temp*_label")
            labels.sort()
            for path in labels:
                label_file = open(path, "r")
                label = label_file.read().strip()
                temperature_file_path = path[:29] + "_input" #should end up with something like 
                                                            #"/sys/class/hwmon/hwmonX/tempY_input" for this label
                temperature_file = open(temperature_file_path, "r")
                temperature = float(temperature_file.read().strip()) / 1000
                temperature_file.close()
                if("Package" in label):
                    # ret[0] = temperature
                    package_temp = temperature
                else: #this is (probably) for a core.
                    core_temps.append(temperature)
                label_file.close()
            return (package_temp, core_temps)
        elif(architecture == "aarch64"):
            temperature_file = open(cpu_hwmon_path + "temp1_input", "r")
            temperature = float(temperature_file.read().strip()) / 1000
            temperature_file.close()
            return (temperature, [])
        else: 
            # This should be unreachable because of the architecture chech in cpu_monitor(), but just in case things 
            # break this happens, an error message is better than an error from trying to serialize None or something 
            # like that.
            logerr("get_cpu_temps(): architecture unsupported.")
            return (float("NaN"), [])
    except: #there is a lot of stuff that can break in the above block...
        logerr("unable to get CPU temperature data")
        return (float("NaN"), []) #was previously None; had to be changed because it must be serializable as a float.


def get_cpu_load(last_cpu_times):
    """Gets the average CPU loads overall and per core since last_cpu_times was collected.
    parameters: 
        last_cpu_times: a 2d list of strings, as produced by get_load_data(). used to calculate a
        change since the last call.

    returns:
        a tuple of(float, float[], str[][]) where the first float is overall CPU load, the second element
        is a list of CPU loads for each CPU core, and the final element is the data most recently received 
        from calling get_load_data() to be used for the next call of this function.
    """

    new_cpu_times = get_load_data()
    overall = None
    per_core = []
    # To get loads, find the difference between the current CPU times since startup and the old ones, then find what
    # percent those times overall and per core as spent not idle, i.e. under load. This could be done faster with 
    # something like numpy, but that would add a (debatably) unnecessary dependency.
    for line_index in range(0, len(last_cpu_times)):
        difference = []
        for i in range(0, len(last_cpu_times[0])):
            difference.append(int(new_cpu_times[line_index][i]) - int(last_cpu_times[line_index][i]))
        idle = float(difference[3]) / float(sum(difference)) # %/100 of time since startup spent in an "idle" state
        load = 1 - idle # %/100 of time since the last data was collected spent not idle, i.e. CPU load.
        if(line_index == 0):
            #note: rounding removed because it seemed that a lot of error would arise when actually sending and 
            #      receiving the messages, so doing so was basically pointless.
            overall = load
        else:
            per_core.append(load)
    #if block added to prevent issues with serializing None as a float
    if(overall != None):
        return (overall, per_core, new_cpu_times)
    else:
        return (float("NaN"), [], new_cpu_times)


def get_load_data():
    """Gets CPU load data from /proc/stat.
    returns:
        A 2d list of strings where each element is a list times spent in various stats since startup, measured in 
        USER_HZ (usually 10ms). The first element is for the system overall, subsequent elements are for specific cores, 
        in order.
        This data comes directly from /proc/stat. more info: https://man7.org/linux/man-pages/man5/proc.5.html
    """
    proc_stat = open("/proc/stat", "r")
    ret = []
    #times_since_startup = proc_stat.readline().strip().split()[1:]
    for line in proc_stat:
        line_split = line.strip().split()
        if(not ("cpu" in line_split[0])): #we have gone past the CPU lines
            break
        else:
            #everything but the label since we know [0] is overall and after that is per core by index
            ret.append(line_split[1:]) 
    proc_stat.close()
    return ret


def gated_loginfo(quiet, msg):
    """Logs a given message (msg) to the ros INFO log depending on the quiet parameter."""

    if(not quiet):
        loginfo(msg)


def cpu_monitor():
    """Publishes CPU data to /bthere/cpu_data."""

    architecture = uname()[4] # This will return 'x86_64', 'aarc64' (for 64 bit arm), etc.
    if(not architecture in SUPPORTED_ARCHITECTURES):
        logerr("This architecture doesn't appear to be one that is supported. Consider adding it and openning" + 
                " a pull request on github!")
        exit()

    init_node("bthere_cpu_monitor", anonymous=False)
    pub = Publisher("/bthere/cpu_data", CPUData, queue_size=10)
    loginfo("Outputting to /bthere/cpu_data")
    
    #update period should to be somewhat small since the cpu load data is average since you last checked,
    #a slower update rate will be less accurate for bursty loads and may introduce more lag than expected
    #if a load is added later in the time between updates for example.
    update_period = get_param('~update_period', 1.0)
    rate = Rate(1/float(update_period))
    loginfo("Publishing rate: " + str(1.0/update_period) + " hz")

    quiet = get_param("~quiet", False)

    #since the temperature-getting seems likely to be failure prone, try it once to check.
    able_to_get_temps = True

    if(isnan(get_cpu_temps(architecture)[0])):
        logwarn("Unable to get CPU temperatures")
        able_to_get_temps = False
    
    last_cpu_times = []
    while not is_shutdown():
        data = CPUData()
        gated_loginfo(quiet, "------ CPU Data ------")
        if(able_to_get_temps):
            package_temp, core_temps = get_cpu_temps(architecture)
            gated_loginfo(quiet, "CPU Package temp. (C): " + str(package_temp))
            data.package_temp = package_temp
            if(len(core_temps) > 0):
                for core in range(len(core_temps)):
                    gated_loginfo(quiet, "CPU Core " + str(core) + "temp. (C): " + str(core_temps[core]))
            data.core_temps = core_temps
        else:
            #data is unavailable so just make it NaN
            gated_loginfo(quiet, "CPU temperatures unavailable")
            data.package_temp = float("NaN")
            data.core_temps = [float("NaN")]
        if(len(last_cpu_times) == 0): #if this hasn't been initialized, we just won't publish this info yet.
            last_cpu_times = get_load_data()
            gated_loginfo(quiet, "CPU load not yet available")
        else:
            overall_load, per_cores, last_cpu_times = get_cpu_load(last_cpu_times)
            gated_loginfo(quiet, "Overall CPU load: " + str(round(overall_load * 100, 1)) + "%")
            data.overall_cpu_load = overall_load
            if(len(per_cores) > 0):
                for core in range(len(per_cores)):
                    gated_loginfo(quiet, "CPU core " + str(core) + " load: " + str(round(per_cores[core] * 100, 1)) + 
                                    "%")
            data.core_loads = per_cores
        data.timestamp = Time.now()
        pub.publish(data)
        rate.sleep()


if __name__ == "__main__":
    try:
        cpu_monitor()
    except ROSInterruptException:
        pass
