# sml_server_time

libsml (https://github.com/volkszaehler/libsml) example project with additional act_sensor_time output.

Basically, sml_server has been modified by just this line:
```
printf("act_sensor_time#%u#\n", *body->act_sensor_time->data.sec_index);
```

