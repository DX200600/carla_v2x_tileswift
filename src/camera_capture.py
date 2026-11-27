import carla
import time
import cv2
import os
import numpy as np
from datetime import datetime

# ===================== 配置 =====================
IMG_W = 800
IMG_H = 600
FOV = 90.0
SAVE_DIR_RGB = "data/raw/rgb"
SAVE_DIR_SEG = "data/raw/semantic"
TARGET_FPS = 20
# ===============================================

os.makedirs(SAVE_DIR_RGB, exist_ok=True)
os.makedirs(SAVE_DIR_SEG, exist_ok=True)

frame_id = 0
rgb_ts_list = []
actor_list = []

def rgb_callback(image):
    global frame_id
    t = time.time()
    rgb_ts_list.append(t)
    img_array = np.frombuffer(image.raw_data, dtype=np.uint8)
    img_array = img_array.reshape((IMG_H, IMG_W, 4))
    img_bgr = img_array[:, :, :3]
    save_path = os.path.join(SAVE_DIR_RGB, f"{frame_id:06d}.png")
    cv2.imwrite(save_path, img_bgr)
    print(f"[RGB] frame={frame_id:06d}, ts={datetime.now()}")
    frame_id += 1

def seg_callback(image):
    global frame_id
    img_array = np.frombuffer(image.raw_data, dtype=np.uint8)
    img_array = img_array.reshape((IMG_H, IMG_W, 4))
    img_bgr = img_array[:, :, :3]
    save_path = os.path.join(SAVE_DIR_SEG, f"{frame_id-1:06d}.png")
    cv2.imwrite(save_path, img_bgr)

def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    bp_lib = world.get_blueprint_library()

    # 生成自车
    vehicle_bp = bp_lib.filter("model3")[0]
    spawn_points = world.get_map().get_spawn_points()
    ego_vehicle = world.spawn_actor(vehicle_bp, spawn_points[0])
    ego_vehicle.set_autopilot(True)
    actor_list.append(ego_vehicle)

    # RGB相机
    rgb_cam_bp = bp_lib.find("sensor.camera.rgb")
    rgb_cam_bp.set_attribute("image_size_x", str(IMG_W))
    rgb_cam_bp.set_attribute("image_size_y", str(IMG_H))
    rgb_cam_bp.set_attribute("fov", str(FOV))
    rgb_cam_bp.set_attribute("sensor_tick", str(1.0 / TARGET_FPS))

    # 语义分割相机
    seg_cam_bp = bp_lib.find("sensor.camera.semantic_segmentation")
    seg_cam_bp.set_attribute("image_size_x", str(IMG_W))
    seg_cam_bp.set_attribute("image_size_y", str(IMG_H))
    seg_cam_bp.set_attribute("fov", str(FOV))
    seg_cam_bp.set_attribute("sensor_tick", str(1.0 / TARGET_FPS))

    cam_transform = carla.Transform(carla.Location(x=0, z=2.0))
    rgb_cam = world.spawn_actor(rgb_cam_bp, cam_transform, attach_to=ego_vehicle)
    seg_cam = world.spawn_actor(seg_cam_bp, cam_transform, attach_to=ego_vehicle)
    actor_list.append(rgb_cam)
    actor_list.append(seg_cam)

    rgb_cam.listen(rgb_callback)
    seg_cam.listen(seg_callback)

    print("✅ 相机启动，Ctrl+C停止采集")
    try:
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n🛑 停止采集，统计FPS")
        if len(rgb_ts_list) >= 2:
            duration = rgb_ts_list[-1] - rgb_ts_list[0]
            avg_fps = (len(rgb_ts_list) - 1) / duration
            print(f"📊 总帧数：{len(rgb_ts_list)}，总时长：{duration:.2f}s，平均FPS = {avg_fps:.2f}")
        else:
            print("帧数不足，无法统计FPS")
    finally:
        print("开始清理相机与自车...")
        for a in actor_list:
            if a.is_alive:
                a.destroy()
        print("✅ 资源释放完成")

if __name__ == "__main__":
    main()
