# -*- coding: utf-8 -*-
import carla
import cv2
import numpy as np
import queue
import threading
import time
import csv

# 线程安全队列
frame_queue = queue.Queue(maxsize=20)
stop_flag = threading.Event()
frame_recv_count = 0
frame_write_count = 0
lock = threading.Lock()

def producer_callback(image):
    """生产者：相机回调，收到帧就入队"""
    global frame_recv_count
    timestamp = image.timestamp
    frame_data = {
        "timestamp": timestamp,
        "height": image.height,
        "width": image.width
    }
    try:
        frame_queue.put_nowait(frame_data)
        with lock:
            frame_recv_count += 1
    except queue.Full:
        print(f"[警告] 队列已满，帧丢弃，时间戳：{timestamp:.4f}")

def consumer_thread(csv_path):
    """消费者线程：出队，写csv"""
    global frame_write_count
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp","height","width"])
        writer.writeheader()
        while not stop_flag.is_set() or not frame_queue.empty():
            try:
                data = frame_queue.get(timeout=0.2)
                writer.writerow(data)
                f.flush()
                with lock:
                    frame_write_count +=1
                frame_queue.task_done()
            except queue.Empty:
                continue

def main():
    client = carla.Client('127.0.0.1', 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    blueprint_lib = world.get_blueprint_library()

    # 车辆
    blueprint_list = blueprint_lib.filter('vehicle.tesla.model3')
    if not blueprint_list:
        raise RuntimeError("找不到 model3 车辆蓝图！")
    car_bp = blueprint_list[0]
    spawn_point = world.get_map().get_spawn_points()[0]
    vehicle = world.spawn_actor(car_bp, spawn_point)
    vehicle.set_autopilot(True)
    print("✅ 车辆生成，开启自动驾驶")

    # 相机
    cam_bp = blueprint_lib.find('sensor.camera.rgb')
    cam_bp.set_attribute('image_size_x','800')
    cam_bp.set_attribute('image_size_y','600')
    cam_bp.set_attribute('fov','90')
    cam_transform = carla.Transform(carla.Location(x=1.5,z=2.4))
    camera = world.spawn_actor(cam_bp, cam_transform, attach_to=vehicle)

    # 绑定回调
    camera.listen(producer_callback)

    csv_save_path = "./data/frame_log_10s.csv"
    cons_th = threading.Thread(target=consumer_thread, args=(csv_save_path,))
    cons_th.start()

    run_duration = 10
    print(f"🚀 开始采集，持续 {run_duration} 秒...")
    time.sleep(run_duration)

    # 停止流程
    stop_flag.set()
    cons_th.join()
    camera.stop()
    camera.destroy()
    vehicle.destroy()

    print("\n====测试结果====")
    print(f"收到总帧数：{frame_recv_count}")
    print(f"写入CSV帧数：{frame_write_count}")
    if frame_recv_count == frame_write_count:
        print("✅ 验证通过：10秒内无丢帧")
    else:
        print(f"❌ 存在丢帧，丢帧数量：{frame_recv_count - frame_write_count}")

if __name__ == "__main__":
    main()
