#!/usr/bin/env python
from rospy import init_node, loginfo, get_param, Publisher, Rate, is_shutdown, ROSInterruptException, Duration
from sensor_msgs.msg import BatteryState
import os


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


def battery_level_monitor():
    init_node('bthere_battery_state_monitor', anonymous=False)
    pub = Publisher('/bthere/battery_state', BatteryState, queue_size=10)

    # update parameters from parameter server or use default values
    update_period = get_param('~update_period', 10)
    rate = Rate(1/float(update_period))
    loginfo('Publishing rate: ' + str(1/float(update_period)) + 'hz')

    while not is_shutdown():

        if (is_tool_present('upower')):

            # Get the battery uri
            cmd_output = os.popen('upower -e').read()
            lines = cmd_output.splitlines()
            for line in lines:
                if (line.find('battery') != -1):
                    battery_uri = line

            # Get the battery information
            cmd_output = os.popen('upower -i ' + battery_uri).read()

            battery_state = BatteryState()
            battery_state.voltage = get_battery_voltage(cmd_output)
            battery_state.current = get_battery_current(cmd_output)
            battery_state.charge = get_battery_charge(cmd_output)
            battery_state.capacity = get_battery_capacity(cmd_output)
            battery_state.design_capacity = get_battery_design_capacity(cmd_output)
            battery_state.percentage = get_battery_percentage(cmd_output)
            battery_state.power_supply_status = get_battery_status(cmd_output)
            battery_state.power_supply_health = get_battery_health(cmd_output)
            battery_state.power_supply_technology = get_battery_technology(cmd_output)
            battery_state.present = get_battery_presence(cmd_output)
            battery_state.cell_voltage = get_battery_cell_voltage(cmd_output)
            battery_state.location = get_battery_path(cmd_output)
            battery_state.serial_number = get_battery_serial_number(cmd_output)

            loginfo('------ Battery State --------------')
            loginfo('Voltage (V): %f' % battery_state.voltage)
            loginfo('Current (A): %f' % battery_state.current)
            loginfo('Charge (Ah): %f' % battery_state.charge)
            loginfo('Capacity (Ah): %f' % battery_state.capacity)
            loginfo('Design capacity (Ah): %f' % battery_state.design_capacity)
            loginfo('Percentage (%%): %f' % battery_state.percentage)
            loginfo('Power supply status: %d' % battery_state.power_supply_status)
            loginfo('Power supply health: %d' % battery_state.power_supply_health)
            loginfo('Power supply technology: %d' % battery_state.power_supply_technology)
            loginfo('Battery present: %r' % battery_state.present)
            loginfo('Cell-voltage: %s' % str(battery_state.cell_voltage)[1:-1])
            loginfo('Location: %s' % battery_state.location)
            loginfo('Serial number: %s' % battery_state.serial_number)

            pub.publish(battery_state)

        rate.sleep()


if __name__ == "__main__":
    try:
        battery_level_monitor()
    except ROSInterruptException:
        pass
