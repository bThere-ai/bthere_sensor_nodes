# bThere sensor nodes
Portable ROS nodes to publish commonly useful sensor data. These nodes were made for use with the Bthere console, but do not depend on it.

# To use

```bash
$ git clone https://github.com/bthere-ai/bthere_sensor_nodes.git
$ cd bthere_sensor_nodes
$ catkin_make
$ source devel/setup.bash
$ roslaunch bthere_sensor_nodes bthere_sensor_nodes.launch
```

# The nodes
All of these nodes support the parameter "quiet" which will disable logging of the data.

All custom messages are in the bthere_sensor_msgs catkin package.
## Wifi signal monitor
Publishes wifi connection strength in dBm. Requires iwconfig and nmcli.

Note that this node publishes a custom message type, WifiData.

### usage:

```bash  
$ roslaunch bthere_wifi_signal_monitor bthere_wifi_signal_monitor.launch
```

## CPU monitor
Publishes overall cpu load, per code loads, CPU package temperature (if possible), and per-core temperatures (if possible). This node is able to publish CPU load data on all linux machines, but cannot get temperature data on all machines (currently). This node has no dependencies.

Note that this node publishes a custom message type, CPUData.

### usage:

```bash
$ roslaunch bthere_cpu_monitor bthere_cpu_monitor.launch
```

## Network monitor
Publishes network usage statistics such as upload rate, download rate, uploaded packets, downloaded packets, etc. This node has no dependencies and seems to work on any ubuntu machine, though the source of its data (/proc/net/dev) is poorly documented.

Note that this node publishes a custom message type, NetworkData.

### usage:

```bash  
$ roslaunch bthere_network_monitor bthere_network_monitor.launch
```

## Battery monitor
Publishes battery data such as voltage, charge, percentage, etc (uses the standard BatteryState message type). Requires upower.

### usage:

```bash
$ roslaunch bthere_battery_state_monitor bthere_battery_state_monitor.launch
```