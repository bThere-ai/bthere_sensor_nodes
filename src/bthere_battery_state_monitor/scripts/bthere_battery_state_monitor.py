#!/usr/bin/env python
from rospy import init_node, loginfo, get_param, Publisher, Rate, is_shutdown, ROSInterruptException, Duration
from sensor_msgs.msg import BatteryState
import os
import argparse


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
    key = key + ':'
    lines = input.splitlines()
    for line in lines:
        if (line.find(key) != -1):
            value = line.split(':')[1].strip()
    return value


def get_battery_path(input):
    return get_named_value(input, 'native-path')


def get_battery_voltage(input):
    voltage_str = get_named_value(input, 'voltage')
    voltage = voltage_str.split()[0]
    return float(voltage)


def get_battery_current(input):
    energy_rate = get_named_value(input, 'energy-rate').split()[0]
    voltage = get_battery_voltage(input)
    return float(energy_rate) / voltage


def get_battery_charge(input):
    energy = get_named_value(input, 'energy').split()[0]
    voltage = get_battery_voltage(input)
    return float(energy) / voltage


def get_battery_capacity(input):
    return float('NaN')


def get_battery_design_capacity(input):
    return float('NaN')


def get_battery_percentage(input):
    return float(get_named_value(input, 'percentage').rstrip('%'))


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
    tech = get_named_value(input, 'technology')
    if (tech == 'lithium-ion'):
        return POWER_SUPPLY_TECHNOLOGY_LION
    else:
        return POWER_SUPPLY_TECHNOLOGY_UNKNOWN


def get_battery_presence(input):
    return True


def get_battery_cell_voltage(input):
    return [float('NaN'), float('NaN'), float('NaN')]


def get_battery_serial_number(input):
    return get_named_value(input, 'serial')


def get_battery_is_charging(input):
    return False if (get_named_value(input, 'state') == 'discharging') else True


def get_battery_duration(input):
    # First get the battery state
    time_remaining_str = '0 hours'
    state = get_named_value(input, 'state')
    if (state == 'discharging'):
        time_remaining_str = get_named_value(input, 'time to empty')
    elif (state == 'charging'):
        time_remaining_str = get_named_value(input, 'time to full')

    time_remaining = time_remaining_str.split()[0]
    time_units = time_remaining_str.split()[1]
    if (time_units == 'hours'):
        duration = Duration.from_sec(float(time_remaining) * 60 * 60)
    elif (time_units == 'minutes'):
        duration = Duration.from_sec(float(time_remaining) * 60)

    return duration


def get_battery_info(test_input_file):
    battery_info = None
    if (test_input_file):
        test_file = open(args.test_input_file, 'r')
        battery_info = test_file.read()
        # print(battery_info)
    else:
        if (is_tool_present('upower')):
            battery_found = False
            # Get the battery uri
            cmd_output = os.popen('upower -e').read()
            lines = cmd_output.splitlines()
            for line in lines:
                if (line.find('battery') != -1):
                    battery_uri = line
                    battery_found = True
            if(battery_found):
                # Get the battery information
                battery_info = os.popen('upower -i ' + battery_uri).read()
    return battery_info


def gated_loginfo(quiet, msg):
    if (not quiet):
        loginfo(msg)


def battery_level_monitor(test_input_file, quiet, update_period):
    init_node('bthere_battery_state_monitor', anonymous=False)
    pub = Publisher('/bthere/battery_state', BatteryState, queue_size=10)

    rate = Rate(1/float(update_period))
    loginfo('Publishing rate: ' + str(1/float(update_period)) + 'hz')

    while not is_shutdown():

        # if (is_tool_present('upower')):
        #     battery_found = False

        #     # Get the battery uri
        #     cmd_output = os.popen('upower -e').read()
        #     lines = cmd_output.splitlines()
        #     for line in lines:
        #         if (line.find('battery') != -1):
        #             battery_uri = line
        #             battery_found = True

        #     if(battery_found):
        #         # Get the battery information
        #         cmd_output = os.popen('upower -i ' + battery_uri).read()
        cmd_output = get_battery_info(test_input_file)
        if (cmd_output is not None):
            battery_state = BatteryState()
            battery_state.voltage = get_battery_voltage(cmd_output)
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


if __name__ == "__main__":
    # parse the command line arguments
    parser = argparse.ArgumentParser(description="bthere_battery_state_monitor",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--test_input_file", dest="test_input_file",
                        help="Input file to use for battery state rather than querying the system")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--quiet", dest="quiet", action='store_true',
                       help="Disable printing to standard out")
    group.add_argument("--chatty", dest="quiet", action='store_false',
                       help="Enable printing to standard out")
    parser.set_defaults(quiet=False)
    parser.add_argument("--update_period", dest="update_period", default=get_param('~update_period', 10),
                        help="Seconds between updates. Type is float.", type=float)
    args = parser.parse_args()
    test_file = None
    if (args.test_input_file is not None):
        if not os.path.exists(args.test_input_file):
            print("The file %s does not exist!" % args.test_input_file)
            exit()

    print("Run with --help to get usage info")

    print(args)

    try:
        battery_level_monitor(test_input_file=args.test_input_file,
                              quiet=args.quiet, update_period=args.update_period)
    except ROSInterruptException:
        pass
