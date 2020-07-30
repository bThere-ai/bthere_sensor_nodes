#!/usr/bin/env python
from rospy import init_node, loginfo, logerr, get_param, Publisher, Rate, is_shutdown, ROSInterruptException, Time
import os
from std_msgs.msg import Header
from bthere_sensor_msgs.msg import WifiData
import sys

test_wifi_values = [-90, -80, -72, -60, -46]
wifi_test_data_index = 0


def publish(pub, signal_level, quiet):
    # Log and publish the wifi signal value
    if (not quiet):
        loginfo('---------- Wifi Signal ------------')
        loginfo('Signal Level: ' + str(signal_level) + ' dBm')
    toPublish = WifiData()
    toPublish.data = int(signal_level)
    toPublish.header = Header(stamp = Time.now())
    #sequential id is automatically set, frame id doesn't matter for this 
    pub.publish(toPublish)


def output_wifi(rate, pub, quiet):
    # Get power using iwconfig

    # Get the active network connection
    cmd_output = os.popen('nmcli dev status').read()
    lines = cmd_output.splitlines()
    has_found_wifi = False
    for line in lines:
        if (line.find('wifi') != -1) and (line.find('connected') != -1):
            has_found_wifi = True
            interface = line.split()[0]
    # Without this check, the script will crash on the next line (cmd_output = ...) if there isn't a wifi device without
    # a clear error message.
    if(not has_found_wifi):
        logerr("No wifi device found.")
        return

    # Get the signal level
    cmd_output = os.popen('iwconfig ' + interface).read()
    lines = cmd_output.splitlines()
    for line in lines:
        if (line.find('Signal level') != -1):
            index = line.find('Signal level')
            signal_level = line[index:].split('=')[1].split()[0]

            publish(pub, signal_level, quiet)


def output_test_data(rate, pub, quiet):
    global test_wifi_values
    global wifi_test_data_index
    wifi_value = test_wifi_values[wifi_test_data_index]
    publish(pub, wifi_value, quiet)
    wifi_test_data_index = (wifi_test_data_index+1) % len(test_wifi_values)


def wifi_signal_monitor():
    init_node('bthere_wifi_signal_monitor', anonymous=False)
    pub = Publisher('/bthere/wifi_signal', WifiData, queue_size=10)
    loginfo('Outputting to /bthere/wifi_signal')
    test_output = get_param('~test_output', False)
    update_period = get_param('~update_period', 15.0)
    quiet = get_param('~quiet', False)

    rate = Rate(1/float(update_period))
    loginfo('Publishing rate: ' + str(1/float(update_period)) + 'hz')

    while not is_shutdown():
        if (test_output):
            output_test_data(rate, pub, quiet)
        else:
            output_wifi(rate, pub, quiet)
        rate.sleep()


def print_help():
    print("Usage: bthere_wifi_signal_monitor [OPTIONS]")
    print("   -h, --help                   this message")
    print("   __log:=FILENAME              the file that the node's log file should be written")
    print("   __name:=NAME                 the name of the node")
    print(
        "   _quiet:={true|false}         suppresses printing of samples to std out. Default is false")
    print(
        "   _test_output:={true|false}   output cyclic test data instead of real data. Default is false")
    print("   _update_period:=DOUBLE       seconds between updates. Default is 15.0")


def check_for_help_request(argv):
    if (len(argv) > 1 and argv[1] == "--help"):
        print_help()
        exit()
    else:
        print("Run with --help to get usage info")


def main():
    check_for_help_request(sys.argv)
    try:
        wifi_signal_monitor()
    except ROSInterruptException:
        pass


if __name__ == "__main__":
    main()
