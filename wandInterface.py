# get the coordinates of want tip from mocap system 
# perform scaling operations 
# prepare to send instructions to drone

from pymavlink import mavutil
from Custom_Mocap_Commands import *
import time
import threading

class mocap_streaming_thread(threading.Thread):
    def __init__(self, thread_name, thread_ID, mocap_connection, init_time):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.thread_name = thread_name
        self.thread_ID = thread_ID
        self.mocap_connection = mocap_connection
        self.init_time = init_time

    def run(self):
        while True:
            time.sleep(.1)

            [wand_pos, wand_rot] = self.mocap_connection.rigid_body_dict[2]

            print(f"Current y (m): {wand_pos[1]}")
            print(f"Current z (m): {wand_pos[0]}")
            print(f"Current x (m): {wand_pos[2]}")


        return


#Main thread:
    
init_time = time.time()

streaming_client = mocap_connect()
is_running = streaming_client.run()

stream = mocap_streaming_thread("stream1", 1, streaming_client, init_time)
stream.start()
time.sleep(5)