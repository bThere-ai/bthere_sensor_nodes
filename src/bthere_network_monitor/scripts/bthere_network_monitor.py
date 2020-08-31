#!/usr/bin/env python

from rospy import *
import time
from bthere_sensor_msgs.msg import NetworkData
from std_msgs.msg import Header

#set to specify unit of published upload/download rate. 1000 for KB/s, 1000000 for MB/s, etc.
RATE_UNIT_SCALAR = 1000
RATE_UNIT = 'kB/s'

# Ignore loopback.
# Add other interfaces you don't want data from to this.
IGNORE_INTERFACES = ['lo']

DATA_INDEXES = {"RX_BYTES":0, "RX_PACKETS":1, "RX_ERRS":2, "RX_DROP":3, "TX_BYTES":8, "TX_PACKETS":9, "TX_ERRS":10, 
                "TX_DROP":11}

def get_all_data(ignored_interfaces):
    """returns a tuple of:
    (timestamp, received bytes, received packets, receiving errors, received packets dropped (local), 
    transmited bytes, transmited packets, transmit errors, transmiting packets dropped (local))
    This data comes from /proc/net/dev. this file has fairly little documentation. more info:
    https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/4/html/reference_guide/s2-proc-dir-net
    https://stackoverflow.com/questions/3521678/what-are-meanings-of-fields-in-proc-net-dev
    """
    timestamp = time.time()
    file = open("/proc/net/dev", "r")
    file.readline() # Discard label lines since the data is always the same
    file.readline()
    interfaces = []
    for line in file:
        line_list = line.strip().replace(":", " ").split()
        if(line_list[0] in ignored_interfaces):
            continue
        else:
            interfaces.append(line_list[1:])
    data = {"RX_BYTES":0, "RX_PACKETS":0, "RX_ERRS":0, "RX_DROP":0, "TX_BYTES":0, "TX_PACKETS":0, 
            "TX_ERRS":0, "TX_DROP":0}
    for interface in interfaces:
        for key in DATA_INDEXES:
            index = DATA_INDEXES[key]
            data[key] += int(interface[index])
        
    file.close()
    return (timestamp, data)


def get_data_rates(old_data, old_timestamp):
    new_timestamp, new_data = get_all_data(IGNORE_INTERFACES)
    delta_time = new_timestamp - old_timestamp
    ret = {}
    ret["RX_RATE"] = (new_data["RX_BYTES"] - old_data["RX_BYTES"]) / (RATE_UNIT_SCALAR * delta_time)
    ret["RX_PACKETS"] = new_data["RX_PACKETS"]
    ret["RX_ERRS"] = new_data["RX_ERRS"]
    ret["RX_DROP"] = new_data["RX_DROP"]

    ret["TX_RATE"] = (new_data["TX_BYTES"] - old_data["TX_BYTES"]) / (RATE_UNIT_SCALAR * delta_time)
    ret["TX_PACKETS"] = new_data["TX_PACKETS"]
    ret["TX_ERRS"] = new_data["TX_ERRS"]
    ret["TX_DROP"] = new_data["TX_DROP"]

    return ret, new_timestamp, new_data


def gated_loginfo(quiet, msg):
    """Logs a given message (msg) to the ros INFO log depending on the quiet parameter."""

    if(not quiet):
        loginfo(msg)


def network_monitor():
    init_node("bthere_network_monitor", anonymous=False)
    pub = Publisher("/bthere/network_data", NetworkData, queue_size=10)
    loginfo("Outputting to /bthere/network_data")

    update_period = get_param('~update_period', 5.0)
    rate = Rate(1/float(update_period))
    loginfo("Publishing rate: " + str(1.0/update_period) + " hz")

    quiet = get_param("~quiet", False)

    last_data = None
    last_timestamp = None

    while not is_shutdown():
        
        gated_loginfo(quiet, "------ Networking Data ------")

        if(last_data == None): 
            # If this hasn't been initialized, we just won't publish this info yet and init.
            last_timestamp, last_data = get_all_data(IGNORE_INTERFACES)
            gated_loginfo(quiet, "Network data not yet available")
        else:
            data, last_timestamp, last_data = get_data_rates(last_data, last_timestamp)

            message = NetworkData()

            gated_loginfo(quiet, "dowload rate: " + str(data["RX_RATE"]) + " " + RATE_UNIT)
            message.rx_rate = data["RX_RATE"]
            gated_loginfo(quiet, "dowload packets total: " + str(data["RX_PACKETS"]))
            message.rx_packets = data["RX_PACKETS"]
            gated_loginfo(quiet, "dowload errors total: " + str(data["RX_ERRS"]))
            message.rx_errors = data["RX_ERRS"]
            gated_loginfo(quiet, "dowload packets dropped total: " + str(data["RX_DROP"]))
            message.rx_drop = data["RX_DROP"]
            
            gated_loginfo(quiet, "upload rate: " + str(data["TX_RATE"]) + " " + RATE_UNIT)
            message.tx_rate = data["TX_RATE"]
            gated_loginfo(quiet, "upload packets total: " + str(data["TX_PACKETS"]))
            message.tx_packets = data["TX_PACKETS"]
            gated_loginfo(quiet, "upload errors total: " + str(data["TX_ERRS"]))
            message.tx_errors = data["TX_ERRS"]
            gated_loginfo(quiet, "upload packets dropped total: " + str(data["TX_DROP"]))
            message.tx_drop = data["TX_DROP"]

            # Add the header information:
            header = Header(stamp=Time.now())
            # The frame_id property seems to be to do with tf frames of reference. That isn't useful for something like 
            # this, so just leave it empty. (this might be the wrong way to do this, but I don't have any other info.)
            # The sequential id is apparently set by the publisher.
            message.header = header
            
            pub.publish(message)
            rate.sleep()



if __name__ == "__main__":
    try:
        network_monitor()
    except ROSInterruptException:
        pass
