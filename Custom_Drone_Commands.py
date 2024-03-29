# Commands that are written specifically for our drone.
#
# Most of the commands are wrappers for a mavlink "command_long_send"
# For each of these you will finish the command with eight values, 
# the first is the configuration and the final seven are specific to
# each command. You always send all seven parameters but most commands 
# don't use all seven, so you still send you still send 0s for the 
# left overs.
# Unless otherwise specified the commands/messages can be found at:
#   https://mavlink.io/en/messages/common.html

# Packages for drone
from pymavlink import mavutil
import time # Used to sleep while the drone ramps up
import threading #Used to create process to constantly send mocap data

###-------------------------------------------------------------------------------------###
###                               Connect to Drone                                      ###
###-------------------------------------------------------------------------------------###
def drone_connect(port):
    """ Connect to the drone:
    input - udp port
    note: Doesn't matter the IP address, but needs the port and that is defined 
          when you startup mavproxy on the pi, which is currently done through ssh
    returns - drone_connection: object representing the connection to the drone
    """
    print("Attempting to connect on port %d" % port)

    # Create the object that represents the drone and will be used for all communication
    # with the drone.
    drone_connection = mavutil.mavlink_connection('udpin:0.0.0.0:%d' % port) 

    drone_connection.wait_heartbeat() #wait until we hear a heartbeat from the copter

    print("Connection success")
    print("Heartbeat from system (system %u component %u)" 
          % (drone_connection.target_system, drone_connection.target_component))

    return drone_connection 


###-------------------------------------------------------------------------------------###
###                                  Take Off                                           ###
###-------------------------------------------------------------------------------------###
def takeoff(drone, mocap_connection, init_time, takeoff_alt):
    """ Takeoff
    Inputs:
        drone:            Drone connection object, obtained from drone_connect(port)
        mocap_connection: A streaming client created from mocap_connect in 
                          Custom_Mocap_Commands
        init_time:        Time in seconds when the main script started 
        takeoff_alt:      Desired altitue, in positive meters. 
    """
    # The drone's coordinate frame is NED, meaning the ground is zero and the higher you go 
    # the more negative a position you have. For readability use takeoff_alt is positive,
    # but for drone commands it needs to be negative:
    #takeoff_alt *= -1

    # Initialize the GPS origin
    #set_gps_global_origin(drone)

    # Here is the list of modes:
    # 0 = stabilize
    # 1 = acro
    # 2 = alt_hold
    # 3 = auto
    # 4 = guided
    # 5 = loiter
    # 6 = rtl
    # 7 = circle
    # Tell the drone to enter one of these modes:
    flight_mode = 2
    drone.mav.set_mode_send(drone.target_system, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, flight_mode) 

    # arm throttle:
    # reminder - the first 0 isn't a parameter, it is the configuration
    # first parameter: 0 = disarm, 1 = arm
    # second parameter: 0 = use safety checks, 21196 = force arm/disarm
    print("Arming Throttle:")
    drone.mav.command_long_send(drone.target_system, drone.target_component, 
                                 mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

    msg = drone.recv_match(type = 'COMMAND_ACK', blocking = True)
    print(msg) #"result: 0" if it executed without error. If you get result: 4, you probably need to set the copter to guided mode.

    # Give the drone time to start up
    time.sleep(2)

    # Send takeoff command to target altitude.
    # reminder - the first 0 isn't a parameter, it is the configuration
    # first parameter: Pitch (degrees) 
    # 2nd and 3rd: Empty
    # 4: Yaw (degrees). If magnetometer isn't present this is ignored
    # 5th and 6th: Lat Long
    # 7th: Desired altitude (meters), should be negative because we're in NED coordinate frame
    
    ##### Trying the Attitude/Thrust method:
    # print("Setting throttle to 0.9:")

    # print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    # time_us = int((time.time()-init_time) * 1.0e6)
    # drone.mav.set_attitude_target_send(time_us, drone.target_system, drone.target_component, 0b00000111, [1,0,0,0], 0, 0, 0, 0.9, [0,0,0])
    
    # receive_mav_message(drone)

    # time.sleep(5)
    
    # print("Setting throttle to 0.5:")
    # print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    # time_us = int((time.time()-init_time) * 1.0e6)
    # drone.mav.set_attitude_target_send(time_us, drone.target_system, drone.target_component, 0, [1,0,0,0], 0, 0, 0, .5, [0,0,0])


    print("Attempting Takeoff:")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    drone.mav.command_long_send(drone.target_system, drone.target_component, 
                                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 30, 0, 0, 0, 0, 0, 0, takeoff_alt)
    receive_mav_message(drone)
    print("Finished takeoff script")

    # Delay until we reach the desired altitude
    # We must update the via mocap repeatedly
    #msg_interval = 0.075 # seconds
   # last_msg_time = time.time()

    # while 1:
    #     current_time = time.time()

    #     if (current_time - last_msg_time) > msg_interval:
    #         last_msg_time = current_time
    #         current_time_us = int(current_time * 1.0e6) # Mavproxy wants micro seconds

    #         # Update the drone's position from the mocap:
    #         # Get info from mocap
    #         [drone_pos, drone_rot] = mocap_connection.rigid_body_dict[1]

    #         # Update drone's current state
    #         update_drone_state(drone, current_time_us, drone_pos, drone_rot)

    #         # Wait for the next LOCAL_POSITION_NED message
    #         msg = drone.recv_match(type='LOCAL_POSITION_NED', blocking=True)
            
    #         print('Current height: ' + str(msg.z*-1.))

    #         # Check if altitude is within a threshold of the target altitude
    #         if msg.z*-1. < takeoff_alt: # z is negative because of drone's NED coordinate frame
    #             print('Takeoff Success') 
    #             break
    # return



###-------------------------------------------------------------------------------------###
###                              Set GPS Origin                                         ###
###-------------------------------------------------------------------------------------###
def set_drone_gps_global_origin(drone):
    # Set the origin of the GPS, accordinig to mavproxy this does not need to be accurate, 
    # just needs to be initialized: https://ardupilot.org/copter/docs/common-optitrack.html
    # 1st param: Target system
    # 2nd, 3rd, 4th: Lat, long, altitude
    # 5th: Time
    drone.mav.set_gps_global_origin_send(drone.target_system, 400150000, -1052705000, 1624000, 0)
    return


###-------------------------------------------------------------------------------------###
###                                   Land                                              ###
###-------------------------------------------------------------------------------------###
# NOT VERIFIED
def land(drone): 
    drone.mav.command_long_send(drone.target_system, drone.target_component, 
                                mavutil.mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, 0, 0, 0, 0, 0)
    return

###-------------------------------------------------------------------------------------###
###                     Update Drone Attitude and Position                              ###
###-------------------------------------------------------------------------------------###
def update_drone_state(drone, connection_time, drone_pos, drone_rot):
    """ Update the drones attitude and position
    Inputs:
        drone: connection to drone, obtained from drone_connect()
        connection_time: time in seconds from when the script began
        drone_pos: list of 3 floats representing the drone position
        drone_rot: list of 4 floats representing the drone's rotation as a quaternion
    NOTE: The position and orientation are in the mocap's coordinate frame, they are
          converted to the drone's coordinate frame here.
    """
    time_us = int(connection_time * 1.0e6)
    drone.mav.att_pos_mocap_send(time_us, (drone_rot[3], drone_rot[0], drone_rot[2], -drone_rot[1]),
                                    drone_pos[0], drone_pos[2], -drone_pos[1])
    return

###-------------------------------------------------------------------------------------###
###                              Mocap Streaming Thread                                 ###
###-------------------------------------------------------------------------------------###
#class definition
class threaded_mocap_streaming(threading.Thread):
    #Constructor for class
    def __init__(self, thread_name, thread_ID, drone_connection, mocap_connection, init_time):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.thread_name = thread_name
        self.threadID = thread_ID
        self.drone_connection = drone_connection
        self.mocap_connection = mocap_connection
        self.init_time = init_time
    # Streaming Loop
    def run(self):
        """ Initialize the drone's GPS, this requires a few updates of the drone's position
        Inputs:
            drone: connection to drone, obtained from drone_connect()
            mocap_connection: connection to mocap, obtained from mocap_connect() in
                            Custom_Mocap_Commands.py
            init_time: Time in seconds when the main script started 
        """
        pause_between_updates = .1 # seconds
        

        # Do it
        while True:

            time.sleep(pause_between_updates)

            # Get info from mocap
            [drone_pos, drone_rot] = self.mocap_connection.rigid_body_dict[1]
            # print(f"Current altitude (m): {drone_pos[1]}")

            # Update drone's current state
            update_drone_state(self.drone_connection, time.time()-self.init_time, drone_pos, drone_rot)
        
        return

###-------------------------------------------------------------------------------------###
###                                Receive Mav Message                                  ###
###-------------------------------------------------------------------------------------###
def receive_mav_message(drone):
    """ Blocks the thread and waits to receive a message from mavlink. Also prints the
    time stamp when the message was received. Used for debugging purposes
    Inputs:
        drone: connection to drone, obtained from drone_connect()
    """
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    msg = drone.recv_match(type = 'COMMAND_ACK', blocking = True)
    print(msg)
    return



