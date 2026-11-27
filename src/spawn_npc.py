import carla
import random
import time

def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    blueprint_library = world.get_blueprint_library()
    spawn_points = world.get_map().get_spawn_points()

    # 配置数量
    NUM_VEHICLES = 15
    NUM_WALKERS = 8

    actor_list = []

    # 生成车辆
    vehicle_bps = blueprint_library.filter("vehicle.*")
    for _ in range(NUM_VEHICLES):
        bp = random.choice(vehicle_bps)
        sp = random.choice(spawn_points)
        veh = world.try_spawn_actor(bp, sp)
        if veh is not None:
            veh.set_autopilot(True)
            actor_list.append(veh)

    # 生成行人 + 行走控制器（0.9.16正确蓝图id）
    walker_bps = blueprint_library.filter("walker.*")
    walker_controller_bp = blueprint_library.find("controller.ai.walker")

    for _ in range(NUM_WALKERS):
        bp = random.choice(walker_bps)
        sp = random.choice(spawn_points)
        walker = world.try_spawn_actor(bp, sp)
        if walker is not None:
            controller = world.try_spawn_actor(walker_controller_bp, carla.Transform(), attach_to=walker)
            if controller is not None:
                actor_list.append(walker)
                actor_list.append(controller)
                controller.start()
                controller.go_to_location(world.get_random_location_from_navigation())

    print(f"✅ 已生成 {NUM_VEHICLES} 车辆，{NUM_WALKERS} 行人，actor总数：{len(actor_list)}")
    print("💡 按 Ctrl+C 清除全部NPC并退出")

    try:
        while True:
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n🛑 开始销毁NPC...")
        for actor in actor_list:
            if actor.is_alive:
                actor.destroy()
        print("✅ 全部NPC清除完毕")

if __name__ == "__main__":
    main()
