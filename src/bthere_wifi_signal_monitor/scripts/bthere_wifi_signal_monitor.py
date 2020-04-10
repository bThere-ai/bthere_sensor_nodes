#!/usr/bin/env python
from rospy import init_node, loginfo, get_param, Publisher, Rate, is_shutdown, ROSInterruptException
import os
from std_msgs.msg import Int32


def wifi_signal_monitor():
    init_node('bthere_wifi_signal_monitor', anonymous=False)
    pub = Publisher('/bthere/wifi_signal', Int32, queue_size=10)

    # update parameters from parameter server or use default values
    update_period = get_param('~update_period', 2)
    rate = Rate(1/float(update_period))
    loginfo('Publishing rate: ' + str(1/float(update_period)) + 'hz')

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
                loginfo('---------- Wifi Signal ------------')
                loginfo('Signal Level: ' + signal_level + ' dBm')
                pub.publish(int(signal_level))

        rate.sleep()


if __name__ == "__main__":
    try:
        wifi_signal_monitor()
    except ROSInterruptException:
        pass
