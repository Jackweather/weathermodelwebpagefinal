import os
import requests
from datetime import datetime, timedelta, timezone
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# --- Clean up old files in grib_files and static/MSLP directories ---
for folder in [os.path.join("Hrrr", "static", "MSLP", "grib_files"), os.path.join("Hrrr", "static", "MSLP")]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = "Hrrr"
mslp_dir = os.path.join(output_dir, "static", "MSLP")
grib_dir = os.path.join(mslp_dir, "grib_files")  # Now inside MSLP
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(mslp_dir, exist_ok=True)

# Get the current UTC date and time and subtract 6 hours
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # Adjust to nearest 6-hour slot

variable_mslma = "MSLMA"

# Function to download GRIB files (structure and time logic matches test.py)
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_mslp = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
                f"&var_{variable_mslma}=on&lev_mean_sea_level=on")
    response = requests.get(url_mslp, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"Downloaded {file_name}")
        return file_path
    else:
        print(f"Failed to download {file_name} (Status Code: {response.status_code})")
        return None

def generate_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    data = ds['mslma'].values / 100  # Convert pressure to hPa
    lats = ds['latitude'].values
    lons = ds['longitude'].values

    fig, ax = plt.subplots(figsize=(10, 7), dpi=850)
    # Use coolwarm colormap for contour lines
    levels = np.arange(np.floor(data.min()), np.ceil(data.max()) + 1, 2)
    cs = ax.contour(
        lons, lats, data.squeeze(),
        levels=levels,
        cmap="coolwarm",
        linewidths=1 # Increased thickness from 1 to 2
    )
    ax.clabel(cs, inline=True, fontsize=8, fmt='%1.0f')

    # Add H and L symbols for highs and lows
    min_idx = np.unravel_index(np.argmin(data), data.shape)
    max_idx = np.unravel_index(np.argmax(data), data.shape)
    ax.text(lons[min_idx], lats[min_idx], 'L', color='blue', fontsize=24, fontweight='bold', ha='center', va='center')
    ax.text(lons[max_idx], lats[max_idx], 'H', color='red', fontsize=24, fontweight='bold', ha='center', va='center')

    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(mslp_dir, f"MSLP_{step:02d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)
    print(f"Generated PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
for step in range(0, 49):
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_png(grib_file, step)
        png_files.append(png_file)

print("All download and PNG creation tasks complete!")
