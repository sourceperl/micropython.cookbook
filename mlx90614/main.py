from mlx90614 import MLX90614
from machine import I2C
from utime import sleep_ms


# init I2C bus and MLX90614 sensor 
# WARNING: default I2C frequency will not work with this sensor (max is 100 KHz)
i2c = I2C(0, freq=100_000)
mlx = MLX90614(i2c)

#  main loop
while True:
    amb_t = mlx.ambient_temp
    obj_t = mlx.object_temp
    print(f'{obj_t:.2f} C (T amb = {amb_t:.2f} C)')
    sleep_ms(500)