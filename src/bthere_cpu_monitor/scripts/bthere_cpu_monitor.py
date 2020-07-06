#!/usr/bin/env python

from rospy import init_node, loginfo, logerr, ROSInterruptException, Publisher, Rate, is_shutdown, get_param
from std_msgs.msg import Int8, Float32
from CPUData.msg import CPUData
from os import listdir
from glob import glob

#expands a list to make sure there is space up to a given index.
def ensure_space_in_list(list, index, fill_with):
    if(index >= len(list)):
        num_needed = index - len(list) + 1
        for i in range(0, num_needed):
            list.append(None)


#returns: a list where item 0 is package temp, and items after that are sequential core temps.
def get_cpu_temps():
    try:
        hwmons = listdir("/sys/class/hwmon")
        ret = []
        cpu_hwmon_path = ""
        for hwmon in hwmons:
            name_file = open("/sys/class/hwmon/" + hwmon + "/name")
            name = name_file.read()
            if("coretemp" in name):
                cpu_hwmon_path = "/sys/class/hwmon/" + hwmon
                name_file.close()
                break
            name_file.close()
        for path in glob(cpu_hwmon_path + "/temp*_label"):
            label_file = open(path)
            label = label_file.read().strip()
            temperature_file_path = path[:29] + "_input" #should end up with something like "/sys/class/hwmon/hwmonX/tempY_input" for this label
            temperature_file = open(temperature_file_path)
            temperature = float(temperature_file.read().strip()) / 1000
            temperature_file.close()
            if("Package" in label):
                ret[0] = temperature
            else: #this is for a core
                core = int(label[5:])
                ensure_space_in_list(ret, core + 1, None)
                ret[core + 1] = temperature
            label_file.close()
        return ret
    except: #there is a lot of stuff that can break in the above block...
        logerr("unable to get CPU temperature data")
        return None

def get_cpu_load(last_cpu_times):
    proc_stat = open("/proc/stat", "r")
    times_since_startup = proc_stat.readline().strip().split()[1:]
    proc_stat.close()
    difference = []
    for i in range(0, len(times_since_startup)):
        difference.append(int(times_since_startup[i]) - int(last_cpu_times[i]))
    idle = float(difference[3]) / float(sum(difference))
    return int(round((1 - idle) * 100))

def get_init_cpu_load():
    proc_stat = open("/proc/stat", "r")
    times_since_startup = proc_stat.readline().strip().split()[1:]
    proc_stat.close()
    return times_since_startup

def cpu_monitor():
    init_node("bthere_cpu_monitor", anonymous=False)
    load_pub = Publisher("/bthere/cpu_load", Int8, queue_size=5)
    
    update_period = get_param('~update_period', 1.0)
    rate = Rate(1/float(update_period))

    able_to_get_temps = False
    temps_pub = None
    if(get_cpu_temps() != None):
        able_to_get_temps = True
        temps_pub = Publisher("/bthere/cpu_temps", CPUData, queue_size = 10)
    
    last_cpu_times = []
    while not is_shutdown():
        if(able_to_get_temps):
            cpu_data_list = get_cpu_temps()
            temps = CPUData()
            temps.package_temp = cpu_data_list[0]
            temps.core_temps = cpu_data_list[1:]
            temps_pub.publish(temps)
        if(len(last_cpu_times) == 0):
            last_cpu_times = get_init_cpu_load()
        else:
            cpu_load = get_cpu_load(last_cpu_times)
            load_pub.publish(cpu_load)
        
        rate.sleep()


if __name__ == "__main__":
    try:
        cpu_monitor()
    except ROSInterruptException:
        pass
