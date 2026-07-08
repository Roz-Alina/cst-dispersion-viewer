import re
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import glob
import os

def unit_cell_dataframe(directory):
    """
    Parse files names in directory and create DataFrame with phase shifts (kx, ky, kxy),
    eigenmode number (mode) eigenmode frequency (f)

    :param directory: path to the folder containing the data files

    :return  pd.DataFrame
        Columns: 'kx', 'ky', 'kxy', 'mode', 'f', 'id'
        'id' is a unique index for each (kx, ky, kxy) combination.
    """
    pattern = re.compile(r'kx_(\d+)_ky_(\d+)_kxy_(\d+)_mode_(\d+)_f_([\d.]+)\.txt$')
    records = []
    for file in os.listdir(directory):
        m = pattern.search(file)
        if m:
            kx_val = int(m.group(1))
            ky_val = int(m.group(2))
            kxy_val = int(m.group(3))
            mode_val = int(m.group(4))
            f_val = float(m.group(5))
            records.append([kx_val, ky_val, kxy_val, mode_val, f_val])
    df = pd.DataFrame(records, columns=['kx', 'ky', 'kxy', 'mode', 'f'])
    df = df.sort_values(['kx', 'ky', 'kxy'], ascending=[True, True, True]).reset_index(drop=True)
    df['id'] = df.groupby(['kx', 'ky', 'kxy']).ngroup()
    return df


def field_from_txt(name, component, plane):
    """
    Extract electric or magnetic field component values in a given plane from CST .txt file

    :param name: path to the field profile extracted from CST
    :param component: field component x, y or z.
    :param plane: plane xy, yz or xz.
    :return: real part of the field component (2d numpy array), imaginary part of the field component (2d numpy array),
             bounds of the grid (in mm)
    """
    comp_cols = {'x': (3, 4), 'y': (5, 6), 'z': (7, 8)}
    if component not in comp_cols:
        raise ValueError(f"Unknown component: {component}. Choose from 'x','y','z'.")
    rcomp, icomp = comp_cols[component]

    plane_cols = {'xy': (0, 1), 'xz': (0, 2), 'yz': (1, 2)}
    if plane not in plane_cols:
        raise ValueError(f"Unknown plane: {plane}. Choose from 'xy','xz','yz'.")
    x1, x2 = plane_cols[plane]

    df = pd.read_csv(name, sep='\s+', header=None, skiprows=2)

    x = df[x1].unique()
    y = df[x2].unique()

    nx = len(x)
    ny = len(y)
    re_field_2d = np.zeros((ny, nx))
    im_field_2d = np.zeros((ny, nx))

    re_field_1d = df[rcomp].values
    im_field_1d = df[icomp].values

    ind = 0
    for i in range(np.shape(re_field_2d)[0]):
        for j in range(np.shape(re_field_2d)[1]):
            re_field_2d[i, j] = re_field_1d[ind]
            im_field_2d[i, j] = im_field_1d[ind]
            ind += 1
    return re_field_2d, im_field_2d, min(x), max(x), min(y), max(y)

class PointBrowser:
    """
    Click on a point to select and highlight it -- the data that
    generated the point will be shown in the lower Axes.  Use the 'n'
    and 'p' keys to browse through the next and previous points
    """

    def __init__(self, fig, axs, arrays, profiles_directory,
                 field_label='H', component='z', option='abs', plane='xy'):

        self.fig = fig
        self.axs = axs
        self.ax_disp = axs[0]
        self.ax_field = axs[1]
        self.arrays = arrays
        self.profiles_directory = profiles_directory
        self.field_label = field_label
        self.component = component
        self.option = option
        self.plane = plane
        self.cbar = None

        self.id_vals = arrays['id']
        self.freq_vals = arrays['f']
        self.kx_vals = arrays['kx']
        self.ky_vals = arrays['ky']
        self.kxy_vals = arrays['kxy']
        self.mode_vals = arrays['mode']

        self.lastind = 0

        # Yellow highlight point
        self.selected, = self.ax_disp.plot([self.id_vals[0]], [self.freq_vals[0]],
                                           'o', ms=12, alpha=0.4, color='yellow', visible=False)

    def on_press(self, event):
        """Keyboard event handler: 'n' next, 'p' previous."""
        if self.lastind is None:
            return
        if event.key not in ('n', 'p'):
            return
        inc = 1 if event.key == 'n' else -1
        new_ind = np.clip(self.lastind + inc, 0, len(self.id_vals) - 1)
        if new_ind != self.lastind:
            self.update(new_ind)

    def on_pick(self, event):
        """Mouse click event: pick the nearest point."""
        if event.artist != self.ax_disp.lines[0]:  # the scatter plot line
            return True
        if not len(event.ind):
            return True

        xdata = event.mouseevent.xdata
        ydata = event.mouseevent.ydata
        distances = ((xdata - self.id_vals[event.ind])**2 + (ydata - self.freq_vals[event.ind])**2)**0.5
        indmin = distances.argmin()
        dataind = event.ind[indmin]

        self.update(dataind)

    def update(self, ind=None):
        """Update the field display for the point at index `ind`."""
        if ind is None:
            ind = self.lastind
        else:
            self.lastind = ind

        # Extract parameters for this point
        kxi = int(self.kx_vals[ind])
        kyi = int(self.ky_vals[ind])
        kxyi = int(self.kxy_vals[ind])
        modei = int(self.mode_vals[ind])
        freq = self.freq_vals[ind]

        # Find the field file
        pattern = f'*kx_{kxi}_ky_{kyi}_kxy_{kxyi}_mode_{modei}*'
        full_pattern = os.path.join(self.profiles_directory, pattern)
        files = glob.glob(full_pattern)
        if not files:
            print(f"File not found for kx={kxi}, ky={kyi}, kxy={kxyi}, mode={modei}")
            return
        fname = files[0]
        print('File:', fname)

        # Read field
        re_field, im_field, x0, x1, y0, y1 = field_from_txt(fname, component=self.component, plane=self.plane)

        self.ax_field.clear()

        if self.option == 'abs':
            data = np.abs(re_field + 1j * im_field)
            norm = data / np.max(data)
            cmap = 'plasma'
            vmin, vmax = 0, 1
            cbar_title = f'|${self.field_label}_{self.component}$|'
        elif self.option == 're':
            norm = re_field / np.max(np.abs(re_field))
            cmap = 'RdBu_r'
            vmin, vmax = -1, 1
            cbar_title = f'real(${self.field_label}_{self.component}$)'
        else:
            norm = im_field / np.max(np.abs(im_field))
            cmap = 'RdBu_r'
            vmin, vmax = -1, 1
            cbar_title = f'imag(${self.field_label}_{self.component}$)'

        im = self.ax_field.imshow(norm, origin='lower', extent=[x0, x1, y0, y1],
                                  cmap=cmap, vmin=vmin, vmax=vmax)
        self.ax_field.set(xlabel = f'{self.plane[0]}, mm', ylabel = f'{self.plane[1]}, mm')

        if self.cbar is None:
            self.cbar = self.fig.colorbar(im, ax=self.ax_field, orientation='vertical', pad=0.02, label=cbar_title)
        else:
            self.cbar.update_normal(im)


        caption_text = (f'$k_x$ = {kxi:1.0f}\n'
                        f'$k_y$ = {kyi:1.0f}\n'
                        f'$k_{{xy}}$ = {kxyi:1.0f}\n'
                        f'$f$ = {freq:1.3f} GHz\n'
                        f'mode {modei}')

        # Text annotation for the field panel
        self.ax_field.text(-0.7, 0.9, caption_text, transform=self.ax_field.transAxes,
                                          va='top', fontsize=10)

        self.selected.set_visible(True)
        self.selected.set_data([self.id_vals[ind]], [self.freq_vals[ind]])
        self.fig.canvas.draw_idle()

    def connect(self):
        """Connect the event handlers to the figure canvas."""
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        self.fig.canvas.mpl_connect('key_press_event', self.on_press)
