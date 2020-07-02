#!/usr/bin/env python
from rospy import init_node, loginfo, logerr, get_param, Publisher, Rate, is_shutdown, ROSInterruptException, Duration
from sensor_msgs.msg import BatteryState
import os
import sys

# Power supply status constants
POWER_SUPPLY_STATUS_UNKNOWN = 0
POWER_SUPPLY_STATUS_CHARGING = 1
POWER_SUPPLY_STATUS_DISCHARGING = 2
POWER_SUPPLY_STATUS_NOT_CHARGING = 3
POWER_SUPPLY_STATUS_FULL = 4

# Power supply health constants
POWER_SUPPLY_HEALTH_UNKNOWN = 0
POWER_SUPPLY_HEALTH_GOOD = 1
POWER_SUPPLY_HEALTH_OVERHEAT = 2
POWER_SUPPLY_HEALTH_DEAD = 3
POWER_SUPPLY_HEALTH_OVERVOLTAGE = 4
POWER_SUPPLY_HEALTH_UNSPEC_FAILURE = 5
POWER_SUPPLY_HEALTH_COLD = 6
POWER_SUPPLY_HEALTH_WATCHDOG_TIMER_EXPIRE = 7
POWER_SUPPLY_HEALTH_SAFETY_TIMER_EXPIRE = 8

# Power supply technology (chemistry) constants
POWER_SUPPLY_TECHNOLOGY_UNKNOWN = 0
POWER_SUPPLY_TECHNOLOGY_NIMH = 1
POWER_SUPPLY_TECHNOLOGY_LION = 2
POWER_SUPPLY_TECHNOLOGY_LIPO = 3
POWER_SUPPLY_TECHNOLOGY_LIFE = 4
POWER_SUPPLY_TECHNOLOGY_NICD = 5
POWER_SUPPLY_TECHNOLOGY_LIMN = 6


def is_tool_present(name):
    from distutils.spawn import find_executable
    return find_executable(name) is not None


def get_named_value(input, key):
    value = None
    key = key + ':'
    lines = input.splitlines()
    for line in lines:
        if (line.find(key) != -1):
            value = line.split(':')[1].strip()
    return value


def get_battery_path(input):
    value = get_named_value(input, 'native-path')
    return value if (value is not None) else ""


def get_battery_voltage(input):
    value = get_named_value(input, 'voltage')
    if (value is not None):
        voltage_str = str(value)
        voltage = voltage_str.split()[0]
        return float(voltage)
    else:
        return None


def get_battery_current(input):
    current = float('NaN')
    value = get_named_value(input, 'energy-rate')
    if (value is not None):
        energy_rate = value.split()[0]
        voltage = get_battery_voltage(input)
        if (voltage is not None):
            current = float(energy_rate) / voltage
    return current


def get_battery_charge(input):
    charge = float('NaN')
    value = get_named_value(input, 'energy')
    if (value is not None):
        energy = value.split()[0]
        voltage = get_battery_voltage(input)
        if (voltage is not None):
            charge = float(energy) / voltage
    return charge


def get_battery_capacity(input):
    return float('NaN')


def get_battery_design_capacity(input):
    return float('NaN')


def get_battery_percentage(input):
    value = get_named_value(input, 'percentage')
    if (value is not None):
        return float(value.rstrip('%'))
    else:
        return float('NaN')


def get_battery_status(input):
    state = get_named_value(input, 'state')
    if (state == 'discharging'):
        return POWER_SUPPLY_STATUS_DISCHARGING
    elif (state == 'charging'):
        return POWER_SUPPLY_STATUS_CHARGING
    elif (state == 'fully-charged'):
        return POWER_SUPPLY_STATUS_FULL
    else:
        return POWER_SUPPLY_STATUS_UNKNOWN


def get_battery_health(input):
    return POWER_SUPPLY_HEALTH_UNKNOWN


def get_battery_technology(input):
    value = get_named_value(input, 'technology')
    if (value == 'lithium-ion'):
        return POWER_SUPPLY_TECHNOLOGY_LION
    else:
        return POWER_SUPPLY_TECHNOLOGY_UNKNOWN


def get_battery_presence(input):
    return True


def get_battery_cell_voltage(input):
    return [float('NaN'), float('NaN'), float('NaN')]


def get_battery_serial_number(input):
    value = get_named_value(input, 'serial')
    return value if (value is not None) else ""


def get_battery_is_charging(input):
    value = get_named_value(input, 'state')
    return False if (value == 'discharging') else True


# Not currently used
def get_battery_duration(input):
    # First get the battery state
    time_remaining_str = '0 hours'
    state = get_named_value(input, 'state')
    if (state is None):
        return float('NaN')
    if (state == 'discharging'):
        time_remaining_str = get_named_value(input, 'time to empty')
    elif (state == 'charging'):
        time_remaining_str = get_named_value(input, 'time to full')
    if (time_remaining_str is None):
        return float('NaN')
    time_remaining = time_remaining_str.split()[0]
    time_units = time_remaining_str.split()[1]
    if (time_units == 'hours'):
        duration = Duration.from_sec(float(time_remaining) * 60 * 60)
    elif (time_units == 'minutes'):
        duration = Duration.from_sec(float(time_remaining) * 60)
    return duration


def get_battery_info(test_input_file):
    battery_info = None
    if (test_input_file is not None and len(test_input_file) > 0):
        test_file = open(test_input_file, 'r')
        battery_info = test_file.read()
        # print(battery_info)
    else:
        if (is_tool_present('upower')):
            battery_found = False
            # Get the battery uri
            cmd_output = os.popen('upower -e').read()
            lines = cmd_output.splitlines()
            for line in lines:
                if (line.find('devices/battery') != -1):
                    battery_uri = line
                    battery_found = True
            if(battery_found):
                # Get the battery information
                battery_info = os.popen('upower -i ' + battery_uri).read()
    return battery_info


def gated_loginfo(quiet, msg):
    if (not quiet):
        loginfo(msg)


def check_if_test_input_exists(filename):
    if (filename is not None and len(filename) > 0):
        if not os.path.exists(filename):
            print("The file %s does not exist!" % filename)
            exit()
    loginfo("File exists: %s" % filename)


def battery_level_monitor():
    init_node('bthere_battery_state_monitor', anonymous=False)
    pub = Publisher('/bthere/battery_state', BatteryState, queue_size=10)
    loginfo('Outputting to /bthere/battery_state')
    test_input_file = get_param('~test_input_file', None)
    update_period = get_param('~update_period', 10.0)
    quiet = get_param('~quiet', False)
    if (test_input_file is not None):
        loginfo('Using test data from %s' % test_input_file)

    rate = Rate(1/float(update_period))
    loginfo('Publishing rate: ' + str(1/float(update_period)) + 'hz')

    while not is_shutdown():

        cmd_output = get_battery_info(test_input_file)
        if (cmd_output is not None):
            battery_state = BatteryState()
            battery_state.voltage = get_battery_voltage(cmd_output)
            if (battery_state.voltage is None):
                logerr('Can\'t read voltage! Invalid status.')
            else:
                battery_state.current = get_battery_current(cmd_output)
                battery_state.charge = get_battery_charge(cmd_output)
                battery_state.capacity = get_battery_capacity(cmd_output)
                battery_state.design_capacity = get_battery_design_capacity(
                    cmd_output)
                battery_state.percentage = get_battery_percentage(cmd_output)
                battery_state.power_supply_status = get_battery_status(
                    cmd_output)
                battery_state.power_supply_health = get_battery_health(
                    cmd_output)
                battery_state.power_supply_technology = get_battery_technology(
                    cmd_output)
                battery_state.present = get_battery_presence(cmd_output)
                battery_state.cell_voltage = get_battery_cell_voltage(
                    cmd_output)
                battery_state.location = get_battery_path(cmd_output)
                battery_state.serial_number = get_battery_serial_number(
                    cmd_output)

                gated_loginfo(quiet, '------ Battery State --------------')
                gated_loginfo(quiet, 'Voltage (V): %f' % battery_state.voltage)
                gated_loginfo(quiet, 'Current (A): %f' % battery_state.current)
                gated_loginfo(quiet, 'Charge (Ah): %f' % battery_state.charge)
                gated_loginfo(quiet, 'Capacity (Ah): %f' %
                              battery_state.capacity)
                gated_loginfo(quiet, 'Design capacity (Ah): %f' %
                              battery_state.design_capacity)
                gated_loginfo(quiet, 'Percentage (%%): %f' %
                              battery_state.percentage)
                gated_loginfo(quiet, 'Power supply status: %d' %
                              battery_state.power_supply_status)
                gated_loginfo(quiet, 'Power supply health: %d' %
                              battery_state.power_supply_health)
                gated_loginfo(quiet, 'Power supply technology: %d' %
                              battery_state.power_supply_technology)
                gated_loginfo(quiet, 'Battery present: %r' %
                              battery_state.present)
                gated_loginfo(quiet, 'Cell-voltage: %s' %
                              str(battery_state.cell_voltage)[1:-1])
                gated_loginfo(quiet, 'Location: %s' % battery_state.location)
                gated_loginfo(quiet, 'Serial number: %s' %
                              battery_state.serial_number)

                pub.publish(battery_state)

        else:
            gated_loginfo(quiet, '------ Battery State --------------')
            gated_loginfo(quiet, 'No battery found!')

        rate.sleep()


def print_help():
    print("Usage: bthere_wifi_signal_monitor [OPTIONS]")
    print("   -h, --help                   this message")
    print("   __log:=FILENAME              the file that the node's log file should be written")
    print("   __name:=NAME                 the name of the node")
    print(
        "   _quiet:={true|false}         suppresses printing of samples to std out. Default is false")
    print("   _test_input_file:=FILENAME   file to use for mock battery info")
    print("   _update_period:=DOUBLE       seconds between updates. Default is 10.0")


def check_for_help_request(argv):
    if (len(argv) > 1 and argv[1] == "--help"):
        print_help()
        exit()
    else:
        print("Run with --help to get usage info")


if __name__ == "__main__":
    check_for_help_request(sys.argv)
    try:
        battery_level_monitor()
    except ROSInterruptException:
        pass
