import carla
import time
import cv2
import os
import numpy as np
from datetime import datetime
import random

# ===================== 配置 =====================
IMG_W = 800
IMG_H = 600
FOV = 90.0
SAVE_DIR_RGB = "data/raw/rgb"
SAVE_DIR_SEG = "data/raw/semantic"
TARGET_FPS = 20
TICK_DT = 1.0 / TARGET_FPS
# ===============================================

os.makedirs(SAVE_DIR_RGB, exist_ok=True)
os.makedirs(SAVE_DIR_SEG, exist_ok=True)

frame_id = 0
rgb_ts_list = []
actor_list = []
last_wall_ts = None


def rgb_callback(image):
    global frame_id, last_wall_ts
    wall_t = time.time()
    sim_t = image.timestamp   # CARLA仿真时间戳，用来校验仿真步长
    rgb_ts_list.append(wall_t)

    img_array = np.frombuffer(image.raw_data, dtype=np.uint8)
    img_array = img_array.reshape((IMG_H, IMG_W, 4))
    img_bgr = img_array[:, :, :3]
    save_path = os.path.join(SAVE_DIR_RGB, f"{frame_id:06d}.png")
    cv2.imwrite(save_path, img_bgr)

    if last_wall_ts is not None:
        wall_delta = wall_t - last_wall_ts
        print(f"[RGB] frame={frame_id:06d}, sim_t={sim_t:.3f}, wall_interval={wall_delta:.4f}s")
    else:
        print(f"[RGB] frame={frame_id:06d}, sim_t={sim_t:.3f}, interval=first")

    last_wall_ts = wall_t
    frame_id += 1


def seg_callback(image):
    global frame_id
    img_array = np.frombuffer(image.raw_data, dtype=np.uint8)
    img_array = img_array.reshape((IMG_H, IMG_W, 4))
    img_bgr = img_array[:, :, :3]
    save_path = os.path.join(SAVE_DIR_SEG, f"{frame_id-1:06d}.png")
    cv2.imwrite(save_path, img_bgr)


def main():
    global frame_id, rgb_ts_list, last_wall_ts

    frame_id = 0
    rgb_ts_list = []
    last_wall_ts = None
    actor_list = []

    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    bp_lib = world.get_blueprint_library()
    tm = client.get_trafficmanager()

    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = TICK_DT
    world.apply_settings(settings)
    tm.set_synchronous_mode(True)

    # 提速配置
    tm.global_percentage_speed_difference(-30)
    tm.set_hybrid_physics_mode(False)
    tm.set_global_distance_to_leading_vehicle(2.0)

    # 生成自车
    vehicle_bp = bp_lib.filter("model3")[0]
    spawn_points = world.get_map().get_spawn_points()
    ego_vehicle = world.spawn_actor(vehicle_bp, random.choice(spawn_points))
    ego_vehicle.set_autopilot(True)
    actor_list.append(ego_vehicle)

    # ✅ 统一接管场景里所有车辆，全部交给这个TM控制
    all_vehicles = world.get_actors().filter("vehicle.*")
    for v in all_vehicles:
        if v.id != ego_vehicle.id:
            v.set_autopilot(True)

    print(f"ego_vehicle generated, id={ego_vehicle.id}")
    print(f"场景内车辆总数：{len(all_vehicles)}，全部交由TM控制")

    # RGB相机
    rgb_cam_bp = bp_lib.find("sensor.camera.rgb")
    rgb_cam_bp.set_attribute("image_size_x", str(IMG_W))
    rgb_cam_bp.set_attribute("image_size_y", str(IMG_H))
    rgb_cam_bp.set_attribute("fov", str(FOV))
    rgb_cam_bp.set_attribute("sensor_tick", str(TICK_DT))

    # 语义分割相机
    seg_cam_bp = bp_lib.find("sensor.camera.semantic_segmentation")
    seg_cam_bp.set_attribute("image_size_x", str(IMG_W))
    seg_cam_bp.set_attribute("image_size_y", str(IMG_H))
    seg_cam_bp.set_attribute("fov", str(FOV))
    seg_cam_bp.set_attribute("sensor_tick", str(TICK_DT))

    cam_transform = carla.Transform(carla.Location(x=1.5, z=2.5))
    rgb_cam = world.spawn_actor(rgb_cam_bp, cam_transform, attach_to=ego_vehicle)
    seg_cam = world.spawn_actor(seg_cam_bp, cam_transform, attach_to=ego_vehicle)
    actor_list.append(rgb_cam)
    actor_list.append(seg_cam)

    rgb_cam.listen(rgb_callback)
    seg_cam.listen(seg_callback)

    print("✅ 同步模式启动｜目标仿真20FPS(0.05s/仿真步)，TM统一管理所有车辆，Ctrl+C停止采集")

    try:
        while True:
            world.tick()
    except KeyboardInterrupt:
        print("\n🛑 停止采集")
        if len(rgb_ts_list) >= 2:
            duration = rgb_ts_list[-1] - rgb_ts_list[0]
            avg_fps = (len(rgb_ts_list) - 1) / duration
            print(f"📊 墙钟统计：总帧数={len(rgb_ts_list)}，总时长={duration:.2f}s，墙钟平均FPS = {avg_fps:.2f}")
        else:
            print("帧数不足，无法统计墙钟FPS")
    finally:
        settings = world.get_settings()
        settings.synchronous_mode = False
        settings.fixed_delta_seconds = None
        world.apply_settings(settings)
        tm.set_synchronous_mode(False)

        print("清理actor...")
        for a in actor_list:
            if a.is_alive:
                a.destroy()
        print("✅ 清理完成")


if __name__ == "__main__":
    main()
