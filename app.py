import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk

# Constants
PROXIMITY_THRESHOLD = 1000  # in meters
# Simulated user roles and credentials
USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

# Initialize session state
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'alert_sent' not in st.session_state:
    st.session_state['alert_sent'] = False

def send_alert_to_unit(unit_type):
    """
    Sends an alert to a specific unit type.
    Args:
        unit_type (str): The type of unit to send the alert to.
    Returns:
        None
    """
    st.session_state['alerts'][unit_type] = True
    st.write(f"Alert sent to {unit_type}!")

def calculate_3d_distance(loc1, loc2):
    """
    Calculates the 3D distance between two locations.
    Args:
        loc1 (tuple): The 3D coordinates of the first location.
        loc2 (tuple): The 3D coordinates of the second location.
    Returns:
        float: The 3D distance between the two locations in meters.
    """
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    distance_3d = math.sqrt(surface_distance**2 + elevation_difference**2)
    return distance_3d

def check_aircraft_proximity(ground_unit_location, aircraft_location):
    """
    Checks if an aircraft is within a certain proximity to a ground unit.
    Args:
        ground_unit_location (tuple): The 3D coordinates of the ground unit.
        aircraft_location (tuple): The 3D coordinates of the aircraft.
    Returns:
        bool: True if the aircraft is within the proximity threshold, False otherwise.
    """
    distance_to_aircraft = calculate_3d_distance(ground_unit_location, aircraft_location)
    if distance_to_aircraft <= PROXIMITY_THRESHOLD:
        return True
    else:
        return False

def send_alert_to_unit(unit_type):
    """
    Sends an alert to a specific unit type.
    Args:
        unit_type (str): The type of unit to send the alert to.
    Returns:
        None
    """

    st.session_state['alert_sent'] = True
    st.write(f"Alert sent to {unit_type}!")

def login_user(username, password):
    """
    Logs in a user with the given username and password.
    
    Args:
        username (str): The username of the user to log in.
        password (str): The password of the user to log in.
    
    Returns:
        None
    """
    for role, credentials in USER_ROLES.items():
        if credentials['username'] == username and credentials['password'] == password:
            st.session_state['user_role'] = role
            st.success(f'Logged in as {role}')
            return
    st.error('Incorrect username or password')

# Login form
if st.session_state['user_role'] is None:
    st.subheader('Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        login_user(username, password)

# App functionality based on user role
else:
    if st.session_state['user_role'] == 'command_center':
        # Command center interface
        st.title('Command Center Dashboard')
        st.title('Aircraft Proximity Alert System')

        # Input fields for the ground unit location
        st.subheader('Ground Unit Location')
        ground_lat = st.number_input('Latitude', value=0.0, format='%f')
        ground_lon = st.number_input('longitude_wgs84(deg)', value=0.0, format='%f')
        ground_elev = st.number_input('Elevation (meters)', value=0.0, format='%f')
        ground_unit_location = (ground_lat, ground_lon, ground_elev)

        # File uploader for the aircraft location CSV
        st.subheader('Upload Aircraft Location CSV')
        csv_file = st.file_uploader("Choose a CSV file", type="csv")

        if csv_file is not None:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(csv_file)

            # In this case, since we're mapping individual points, each "path" is just one point
            df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

            # Create a single path that connects all the points
            # This assumes that the CSV file is ordered by the flight sequence
            flight_path = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

            # Define the initial view state of the map
            view_state = pdk.ViewState(
                latitude=df['latitude_wgs84(deg)'].mean(),
                longitude=df['longitude_wgs84(deg)'].mean(),
                zoom=11,
                pitch=50,
            )

            # Create a path layer for the flight path
            path_layer = pdk.Layer(
                "PathLayer",
                data=pd.DataFrame({'path': [flight_path]}),  # Wrap the single flight path in a DataFrame
                pickable=True,
                get_color=[255, 0, 0, 150],  # Red color for the path
                width_scale=20,
                width_min_pixels=2,
                get_path="path",
                get_width=5,
            )

            # Create the deck.gl map
            r = pdk.Deck(
                layers=[path_layer],
                initial_view_state=view_state,
                map_style="mapbox://styles/mapbox/light-v9",  # You can choose a different map style
            )

            # Render the deck.gl map in the Streamlit app
            st.pydeck_chart(r)
            # Check if the CSV has the required columns
            if all(col in df.columns for col in ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']):
                # Loop through the DataFrame to simulate aircraft motion
                for index, row in df.iterrows():
                    aircraft_location = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
                    alert = check_aircraft_proximity(ground_unit_location, aircraft_location)

                    if alert:
                        st.error(f'Alert: Aircraft at index {index} is within the proximity threshold!')
                        # Use the index to create a unique key for the radio widget
                        priority_key = f'alert_priority_radio_{index}'
                        priority = st.radio("Who should receive the alert first?",
                                            ('Ground Unit', 'Aircraft'),
                                            key=priority_key)
                        # Use the index to create a unique key for the button widget
                        send_alert_key = f'send_alert_button_{index}'
                        if st.button('Send Alert', key=send_alert_key):
                            unit_type = 'ground_unit' if priority == 'Ground Unit' else 'aircraft'
                            send_alert_to_unit(unit_type)
                            st.session_state['alert_sent'] = True
                            time.sleep(2)
                    elif st.session_state['alert_sent']:
                    # Alert has been sent, continue to next iteration
                        continue
            else:
                st.error('CSV file must contain latitude, longitude, and elevation columns.')

        # Button to check proximity
        if st.button('Check Aircraft Proximity'):
            alert = check_aircraft_proximity(ground_unit_location, aircraft_location)
            if alert:
                st.error('Alert: Aircraft is within the proximity threshold!')

    elif st.session_state['user_role'] == 'ground_unit':
        # Ground unit interface
        st.title('Ground Unit Dashboard')
        if st.session_state['alert_sent']:
            st.error('Alert: You are within the proximity threshold of an aircraft!')

    elif st.session_state['user_role'] == 'aircraft':
        # Aircraft interface
        st.title('Aircraft Dashboard')
        if st.session_state['alert_sent']:
            st.error('Alert: You are within the proximity threshold of the ground unit!')

# Logout button
if st.session_state['user_role'] is not None:
    if st.button('Logout'):
        st.session_state['user_role'] = None
        st.session_state['alert_sent'] = False
        st.write("You have been logged out.")


