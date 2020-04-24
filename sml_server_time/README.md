# sml_server_time

libsml (https://github.com/volkszaehler/libsml) example project with additional act_sensor_time output.



## Problem Statement
Normal `sml_server` example binary from libsml does not output the act_sensor_time field. But I need that.


## Solution Approach
Use the libsml example code `examples/sml_server` (https://github.com/volkszaehler/libsml/blob/master/examples/sml_server.c) and modify it to also output the sensor time.

Basically, sml_server has been modified by just this line:
```
printf("act_sensor_time#%u#\n", *body->act_sensor_time->data.sec_index);
```

## How-To Build
1. Run `bash build.sh`
2. Use binary `sml_server_time` on byte stream / serial port.


## Example 
After building run:  
`./sml_server_time ../example/ISKRA_MT691_eHZ-MS2020.bin`
 
This should produce a textual output like:   
```
1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#198927.3#Wh
1-0:16.7.0*255#26#W
act_sensor_time#6825875#
...
```
