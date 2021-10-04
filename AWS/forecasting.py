"""
Author: David Jorge

This library handles forecasting and simulating ocean pollution drift.

Ocean current data obtained from https://podaac.jpl.nasa.gov/dataset/OSCAR_L4_OC_third-deg.
Credit:
ESR. 2009. OSCAR third deg. Ver. 1. PO.DAAC, CA, USA. Dataset accessed [2021-08-28] at https://doi.org/10.5067/OSCAR-03D01
"""

from datetime import timedelta
import xarray as xr
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy
import numpy as np
from parcels import FieldSet, ParticleSet, JITParticle, AdvectionRK4
import pullS3


class forecasting:
    """
    Class for managing the drift simulations
    """

    def __init__(self, lats, lons, sim_fname):
        """
        Class constructor.

        :param lats: list of the latitude of the points to simulate.
        :param lons: list of the longitude of the points to simulate.
        :param sim_fname: file name for simulation raw data output.
        """
        self.lats = lats
        self.lons = lons
        self.sim_fname = sim_fname

    def update_particles(self, lats, lons):
        """
        Updates latitude and longitude list instance variables.

        :param lats: Updated latitude list.
        :param lons: Updated longitude list.
        """
        self.lats = lats
        self.lons = lons

    def run_forecasting(self, days):
        """
        Runs the simulation on the points stored in the class instance variables and saves the raw output to a file.

        :param days: Number of days in the future to forecast drift.
        """
        # import netCDF4 as nc
        # fn = 'ocean_currents_U.nc'
        # ds = nc.Dataset(fn)
        # print(ds)

        # fname = 'ocean_currents_V.nc'

        # Get ocean current data from files
        filenames = {'U': 'ocean_currents_U.nc', 'V': 'ocean_currents_V.nc'}
        variables = {'U': 'u', 'V': 'v'}
        dimensions = {'U': {'lat': 'latitude', 'lon': 'longitude', 'time': 'time'},
                      # In the GlobCurrent data the dimensions are also called 'lon', 'lat' and 'time'
                      'V': {'lat': 'latitude', 'lon': 'longitude', 'time': 'time'}}

        # Initialize fieldset class instance for simulation (defines the 'field' of the simulation)
        fieldset = FieldSet.from_netcdf(filenames, variables, dimensions)

        # Initialize the particleset class instance for simulation (defines the 'particles' to be simulated)
        pset = ParticleSet(fieldset=fieldset,  # the fields on which the particles are advected
                           pclass=JITParticle,  # the type of particles (JITParticle or ScipyParticle)
                           lon=self.lons,  # release longitude
                           lat=self.lats)  # release latitude

        # pset = ParticleSet.from_line(fieldset=fieldset, size=5, pclass=JITParticle,
        #                             start=(-23, 52), finish=(-23, 53))

        # Initialize particlefile class instance for saving raw simulation output to a file
        output_file = pset.ParticleFile(name=self.sim_fname, outputdt=timedelta(hours=1))

        # Run simulation
        pset.execute(AdvectionRK4, runtime=timedelta(days=days), dt=timedelta(minutes=5), output_file=output_file)

        # pset.show(domain={'N': -31, 'S': -35, 'E': 33, 'W': 26})

        # Only want raw data as .nc file
        output_file.close()

        # plotTrajectoriesFile(self.sim_fname, mode='movie2d')
        print("Simulation Complete!")

    def output_sim(self):
        """
        Save raw simulation data as an mp4 file. Plots background for UI convinience.
        """
        # Load raw simulation data from file
        filename = self.sim_fname
        pfile = xr.open_dataset(str(filename), decode_cf=True)
        lon = np.ma.filled(pfile.variables['lon'], np.nan)
        lat = np.ma.filled(pfile.variables['lat'], np.nan)
        time = np.ma.filled(pfile.variables['time'], np.nan)

        # print(time)
        pfile.close()

        # Get animation time intervals
        plottimes = np.arange(time[0, 0], np.nanmax(time), np.timedelta64(1, 'h'))

        # print(plottimes)
        starttime = 0
        b = time == plottimes[0 + starttime]

        # Initialize animation figure
        fig = plt.figure(figsize=(8, 4))
        # gs = gridspec.GridSpec(ncols=8, nrows=4, figure=fig)

        ### Plot Background and Points
        ax1 = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax1.set_facecolor('#1EB7D0')
        ax1.add_feature(cartopy.feature.LAND, zorder=1)
        ax1.coastlines()
        lat1, lon1, lat2, lon2 = -44, 10, 35, 70
        ax1.set_extent([lat1, lon1, lat2, lon2], crs=ccrs.PlateCarree())
        scat1 = ax1.scatter(lon[b], lat[b], marker='.', s=95, c='#AB2200', edgecolor='white', linewidth=0.15,
                            transform=ccrs.PlateCarree())

        frames = np.arange(0, len(plottimes))

        # Define function for updating figure for each frame
        def animate(t):
            b = time == plottimes[t + starttime]
            scat1.set_offsets(np.vstack((lon[b], lat[b])).transpose())
            # scat2.set_offsets(np.vstack((lon[b], lat[b])).transpose())
            return scat1  # , scat2

        # Save animation to mp4 file
        anim = animation.FuncAnimation(fig, animate, frames=frames, interval=150, blit=False)
        fig.canvas.draw()  # needed for tight_layout to work with cartopy
        plt.tight_layout()
        # writergif = PillowWriter(fps=30)
        # Set up formatting for the movie files
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=30, metadata=dict(artist='Me'), bitrate=1800)
        anim.save('assets/sim.mp4', writer=writer)
        print("Saved Animation!")


if __name__ == "__main__":
    import netCDF4 as nc

    aws = pullS3.pullS3()
    aws.pull()

    # https://podaac.jpl.nasa.gov/dataset/OSCAR_L4_OC_third-deg

    obj = forecasting(aws.map_data['lat'].tolist(), aws.map_data['lon'].tolist(), "particle_sim.nc")
    obj.run_forecasting(days=14)
    obj.output_sim()

    # fname = 'GlobCurrent_example_data/*.nc'
    # filenames = {'U': fname, 'V': fname}
    # variables = {'U': 'eastward_eulerian_current_velocity', 'V': 'northward_eulerian_current_velocity'}
    # dimensions = {'U': {'lat': 'lat', 'lon': 'lon', 'time': 'time'},
    #              # In the GlobCurrent data the dimensions are also called 'lon', 'lat' and 'time'
    #              'V': {'lat': 'lat', 'lon': 'lon', 'time': 'time'}}
    # fieldset = FieldSet.from_netcdf(filenames, variables, dimensions)

    # pset = ParticleSet(fieldset=fieldset,  # the fields on which the particles are advected
    #                   pclass=JITParticle,  # the type of particles (JITParticle or ScipyParticle)
    #                   lon=26,  # release longitude
    #                   lat=-33)  # release latitude

    # output_file = pset.ParticleFile(name="GCParticles.nc",
    #                                outputdt=3600)  # the file name and the time step of the outputs

    # pset.execute(AdvectionRK4,  # the kernel (which defines how particles move)
    #             runtime=86400 * 300,  # the total length of the run in seconds
    #             dt=300,  # the timestep of the kernel
    #             output_file=output_file)
    # output_file.close()
