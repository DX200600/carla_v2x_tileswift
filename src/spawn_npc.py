import carla
import random
import time
import signal
import sys

actor_list = []

def signal_handler(sig, frame):
    print("\n🛑 收到停止信号，清理NPC actor")
    for a in actor_list:
        if a.is_alive:
            a.destroy()
    print("✅ NPC全部清理完毕，退出")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    blueprint_library = world.get_blueprint_library()
    spawn_points = world.get_map().get_spawn_points()

    NUM_VEHICLES = 4
    # 只生成车，不自动开autopilot！交给采集脚本的TM统一管理
    vehicle_bps = blueprint_library.filter("vehicle.*")
    for _ in range(NUM_VEHICLES):
        bp = random.choice(vehicle_bps)
        spawn_tf = random.choice(spawn_points)
        try:
            veh = world.spawn_actor(bp, spawn_tf)
            actor_list.append(veh)
        except Exception as e:
            print(f"生成NPC失败：{e}")
    print(f"✅ 已生成 {len(actor_list)} 台NPC车辆，等待TM接管控制")

    while True:
        time.sleep(0.2)

if __name__ == "__main__":
    main()
