from dispersion_viewer_utils import *
import matplotlib.pyplot as plt

# -------------------- USER SETTINGS --------------------
profiles_directory = 'unit_cell_data/h_field/'   # path to your data
field_label = 'H'          # 'E' or 'H'
component = 'z'            # 'x', 'y', or 'z'
option = 'im'              # 'abs', 're', or 'im'
plane = 'xy'               # 'xy', 'xz', or 'yz'
# ------------------------------------------------------

# Load the dispersion data
df = unit_cell_dataframe(profiles_directory)

f = df["f"].values
kx = df["kx"].values
ky = df["ky"].values
kxy = df["kxy"].values
mode = df["mode"].values
id_k = df["id"].values

arrays = {
    'id': id_k,
    'f': f,
    'kx': kx,
    'ky': ky,
    'kxy': kxy,
    'mode': mode
}

# Define high-symmetry point coordinates and labels
HSP_conditions = [
    {'kx': 0,   'ky': 0,   'kxy': 0},
    {'kx': 180, 'ky': 0,   'kxy': 0},
    {'kx': 180, 'ky': 180, 'kxy': 0},
    {'kx': 180, 'ky': 180, 'kxy': 180}
]
HSP_labels = ['$\Gamma$', 'X', 'M', '$\Gamma$']
HSP_coords = []
for cond in HSP_conditions:
    mask = (df['kx'] == cond['kx']) & (df['ky'] == cond['ky']) & (df['kxy'] == cond['kxy'])
    row = df[mask]
    if not row.empty:
        HSP_coords.append(row['id'].iloc[0])
    else:
        HSP_coords.append(None)

# Plotting
fig, axs = plt.subplots(2, 1, figsize=(6, 7))
ax_disp = axs[0]
ax_field = axs[1]
line, = ax_disp.plot(id_k, f, '.', picker=True, pickradius=2)
ax_disp.set_ylabel('$f$, GHz')
ax_disp.set_xticks(HSP_coords, HSP_labels)

cbar_ax = None

# Create the browser and connect events
browser = PointBrowser(
    fig=fig,
    axs=axs,
    arrays=arrays,
    profiles_directory=profiles_directory,
    field_label=field_label,
    component=component,
    option=option,
    plane=plane
)
browser.connect()

# Show initial field (first point)
browser.update(0)
plt.show()