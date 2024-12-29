import streamlit as st
import googlemaps
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import random

# Initialize Google Maps Client
API_KEY = st.secrets["API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)


def plus_code_to_coordinates(plus_code):
    try:
        geocode_result = gmaps.geocode(plus_code)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            return None
    except Exception as e:
        st.error(f"Error converting Plus Code {plus_code}: {e}")
        return None

def calculate_distance_matrix(origins, destination):
    try:
        result = gmaps.distance_matrix(origins, [destination], mode="driving")
        distances = [row["elements"][0]["distance"]["value"] for row in result["rows"]]
        return distances
    except Exception as e:
        st.error(f"Error calculating distance matrix: {e}")
        return []

def refine_midpoint(coords):
    if not coords:
        return None

    # Initial guess: geometric midpoint
    avg_lat = sum(coord[0] for coord in coords) / len(coords)
    avg_lng = sum(coord[1] for coord in coords) / len(coords)
    midpoint = [avg_lat, avg_lng]

    # Iteratively refine the midpoint
    for _ in range(5):  # Perform 5 iterations for refinement
        distances = calculate_distance_matrix(coords, midpoint)
        if not distances:
            break

        # Weighted adjustment of the midpoint
        total_weight = sum(1 / d for d in distances if d > 0)
        weighted_lat = sum(coord[0] / d for coord, d in zip(coords, distances) if d > 0)
        weighted_lng = sum(coord[1] / d for coord, d in zip(coords, distances) if d > 0)

        midpoint[0] = weighted_lat / total_weight
        midpoint[1] = weighted_lng / total_weight

    return midpoint

def plot_map(coords, midpoint):
    # Initialize map at the midpoint
    m = folium.Map(location=midpoint, zoom_start=10)

    # Add markers for each coordinate
    for i, coord in enumerate(coords):
        distance = geodesic(coord, midpoint).kilometers  # Calculate distance in kilometers
        folium.Marker(location=coord, popup=f"Point {i + 1}").add_to(m)

    # Add marker for the midpoint
    folium.Marker(location=midpoint, popup="Midpoint", icon=folium.Icon(color="red")).add_to(m)

    # Return the map
    return m

def main():
    st.title("Midpoint Calculator Using Google Plus Codes")

    # Initialize session state
    if "coords" not in st.session_state:
        st.session_state["coords"] = []
    if "midpoint" not in st.session_state:
        st.session_state["midpoint"] = None

    st.write("Enter multiple Google Plus Codes (one per line):")

    input_codes = st.text_area("Google Plus Codes", "")

    if st.button("Calculate Midpoint"):
        if not input_codes.strip():
            st.warning("Please enter at least one Plus Code.")
            return

        plus_codes = [code.strip() for code in input_codes.splitlines() if code.strip()]

        st.write("### Entered Plus Codes:")
        st.write(plus_codes)

        coords = []

        for code in plus_codes:
            coord = plus_code_to_coordinates(code)
            if coord:
                coords.append(coord)

        if not coords:
            st.error("Could not retrieve any valid coordinates from the Plus Codes.")
            return

        # Store the results in session state
        st.session_state["coords"] = coords
        st.session_state["midpoint"] = refine_midpoint(coords)

    # Retrieve from session state
    coords = st.session_state.get("coords", [])
    midpoint = st.session_state.get("midpoint", None)

    if coords and midpoint:
        st.success(f"The refined midpoint is at coordinates: {midpoint}")

        # Calculate and display distances
        st.write("### Distances from Points to Midpoint:")
        distances = []
        for i, coord in enumerate(coords):
            distance = geodesic(coord, midpoint).kilometers  # Calculate distance in kilometers
            distances.append((f"Point {i + 1}", distance))
            st.write(f"Point {i + 1}: {distance:.2f} km")

        # Plot the map
        map_object = plot_map(coords, midpoint)
        st_folium(map_object, width=700, height=500)

if __name__ == "__main__":
    main()
