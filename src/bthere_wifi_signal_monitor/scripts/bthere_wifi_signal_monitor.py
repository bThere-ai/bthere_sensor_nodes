#!/usr/bin/env python
from rospy import init_node, loginfo, get_param, Publisher, Rate, is_shutdown, ROSInterruptException
import os
from std_msgs.msg import Int32
import sys
import argparse


def output_wifi(rate, pub, no_print):
    while not is_shutdown():
        # Get power using iwconfig

        # Get the active network connection
        cmd_output = os.popen('nmcli dev status').read()
        lines = cmd_output.splitlines()
        for line in lines:
            if (line.find('wifi') != -1) and (line.find('connected') != -1):
                interface = line.split()[0]

        # Get the signal level
        cmd_output = os.popen('iwconfig ' + interface).read()
        lines = cmd_output.splitlines()
        for line in lines:
            if (line.find('Signal level') != -1):
                index = line.find('Signal level')
                signal_level = line[index:].split('=')[1].split()[0]

                # Log and publish the wifi signal value
                if (not no_print):
                    loginfo('---------- Wifi Signal ------------')
                    loginfo('Signal Level: ' + signal_level + ' dBm')
                pub.publish(int(signal_level))

        rate.sleep()


def output_test_date(rate, pub, no_print):
    wifi_values = [-90, -80, -72, -60, -46]
    current_index = 0
    while not is_shutdown():
        wifi_value = wifi_values[current_index]
        if (not no_print):
            loginfo('Emitting test_output: ' + str(wifi_value))
        pub.publish(int(wifi_value))
        current_index = (current_index+1) % len(wifi_values)

        rate.sleep()


def wifi_signal_monitor(test_output, update_period, no_print):
    init_node('bthere_wifi_signal_monitor', anonymous=False)
    pub = Publisher('/bthere/wifi_signal', Int32, queue_size=10)

    rate = Rate(1/float(update_period))
    loginfo('Publishing rate: ' + str(1/float(update_period)) + 'hz')

    if (test_output):
        output_test_date(rate, pub, no_print)
    else:
        output_wifi(rate, pub, no_print)


def main():
    # parse the command line arguments
    parser = argparse.ArgumentParser(description="bthere_wifi_signal_monitor",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--test_output", action="store_true",
                        help="Enable cyclic test output")
    parser.add_argument("--no_print", action="store_true",
                        help="Disable printing to standard out")
    parser.add_argument("--update_period", dest="update_period", default=get_param('~update_period', 2),
                        help="Seconds between updates", type=float)
    args = parser.parse_args()

    print("Run with --help to get usage info")

    try:
        wifi_signal_monitor(test_output=args.test_output,
                            update_period=args.update_period,
                            no_print=args.no_print)
    except ROSInterruptException:
        pass


if __name__ == "__main__":
    main()
