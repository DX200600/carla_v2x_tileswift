# src/prod_cons_exercise.py
import threading
import queue
import time
import csv
import numpy as np

# ----------------------配置参数----------------------
QUEUE_MAXSIZE = 64      # 队列最大缓冲，模拟内存上限
RUN_SECONDS = 10        # 运行总时长10秒
IMG_SHAPE = (48, 64)    # 模拟图片尺寸

# 线程安全队列
q = queue.Queue(maxsize=QUEUE_MAXSIZE)
stop_event = threading.Event()   # 停止信号，用来通知线程退出

# 共享计数器：多线程修改，一定要加锁保护
produce_cnt = 0
consume_cnt = 0
cnt_lock = threading.Lock()


def producer():
    """生产者：模拟相机，不断产生“图像”numpy数组放入队列"""
    global produce_cnt
    rng = np.random.default_rng()
    while not stop_event.is_set():
        # 模拟生成一帧图像
        fake_frame = rng.integers(0, 256, size=IMG_SHAPE, dtype=np.uint8)
        try:
            # put增加timeout，不会永久卡死；队列满就循环回来检查stop_event
            q.put(fake_frame, timeout=0.2)
            with cnt_lock:
                produce_cnt += 1
        except queue.Full:
            continue


def consumer():
    """消费者：取帧、计算、写csv"""
    global consume_cnt
    with open("frame_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "frame_id", "mean", "std"])

        while True:
            # 退出条件：收到停止信号 AND 队列已经空了
            if stop_event.is_set() and q.empty():
                break
            try:
                frame = q.get(timeout=0.1)
                now = time.time()
                mean_val = float(np.mean(frame))
                std_val = float(np.std(frame))

                with cnt_lock:
                    consume_cnt += 1
                    fid = consume_cnt

                writer.writerow([now, fid, mean_val, std_val])
                q.task_done()  # 标记队列任务完成
            except queue.Empty:
                # 超时没拿到数据，继续循环
                continue


if __name__ == "__main__":
    t_prod = threading.Thread(target=producer, daemon=True)
    t_cons = threading.Thread(target=consumer, daemon=True)

    t_prod.start()
    t_cons.start()

    print(f"开始运行，持续 {RUN_SECONDS} s ...")
    time.sleep(RUN_SECONDS)

    # 修复逗号bug stop_event.set()
    stop_event.set()
    # 等待两个线程全部执行完毕（消费者会消化完队列残留）
    t_prod.join()
    t_cons.join()

    print("====实验结束统计====")
    print(f"生产帧数：{produce_cnt}")
    print(f"消费帧数：{consume_cnt}")
    if produce_cnt == consume_cnt:
        print("校验通过，没有丢帧")
    else:
        print(f"校验失败！丢帧或者重复处理，差值：{produce_cnt-consume_cnt}")
