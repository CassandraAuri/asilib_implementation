def trex_rgb(
    location_code: str,
    time: utils._time_type = None,
    time_range: utils._time_range_type = None,
    alt: int = 110,
    custom_alt: bool = False,
    redownload: bool = False,
    missing_ok: bool = True,
    load_images: bool = True,
    colors: str = 'rgb',
    burst: bool = False,
    imager=asilib.Imager,
) -> asilib.imager.Imager:
    # TODO: Remove the warning in 2024.
    """
    Create an Imager instance using the TREX-RGB ASI images and skymaps.

    Transition Region Explorer (TREx) RGB data is courtesy of Space Environment Canada (space-environment.ca). Use of the data must adhere to the rules of the road for that dataset.  Please see below for the required data acknowledgement. Any questions about the TREx instrumentation or data should be directed to the University of Calgary, Emma Spanswick (elspansw@ucalgary.ca) and/or Eric Donovan (edonovan@ucalgary.ca).

    “The Transition Region Explorer RGB (TREx RGB) is a joint Canada Foundation for Innovation and Canadian Space Agency project developed by the University of Calgary. TREx-RGB is operated and maintained by Space Environment Canada with the support of the Canadian Space Agency (CSA) [23SUGOSEC].”

    For more information see: https://www.ucalgary.ca/aurora/projects/trex.

    .. warning::

        In early October 2023 the TREx-RGB data format changed, which resulted in a "ValueError: 
        A problematic PGM file..." exception for asilib versions <= 0.20.1. If you're having this 
        issue, you'll need to upgrade asilib to version >= 0.20.2 and delete the outdated TREx RGB
        image files. The code below is the simplest solution:

        .. code-block:: python

            import os
            import shutil

            os.system("pip install aurora-asi-lib -U")

            import asilib

            shutil.rmtree(asilib.config['ASI_DATA_DIR'] / 'trex' / 'rgb')

    Parameters
    ----------
    location_code: str
        The ASI's location code (four letters).
    time: str or datetime.datetime
        A time to look for the ASI data at. Either time or time_range
        must be specified (not both or neither).
    time_range: list of str or datetime.datetime
        A length 2 list of string-formatted times or datetimes to bracket
        the ASI data time interval.
    alt: int
        The reference skymap altitude, in kilometers.
    custom_alt: str, default None
        When selected, there are two options for skyma's between official sky maps:
        If 'Geodetic', asilib will calculate (lat, lon) skymaps assuming a spherical Earth. Otherwise, it will use the official skymaps (Courtesy of University of Calgary).

        .. note::
        
            The spherical model of Earth's surface is less accurate than the oblate spheroid geometrical representation. Therefore, there will be a small difference between these and the official skymaps.

        If 'Interp', asilib will calculate the (lat,lon) sky maps assuming that the interpolation between official maps is linear. This was supported by personal conversations with Dr. Eric Donvan of the University of Calgary
    redownload: bool
        If True, will download the data from the internet, regardless of
        wether or not the data exists locally (useful if the data becomes
        corrupted).
    missing_ok: bool
        Wether to allow missing data files inside time_range (after searching
        for them locally and online).
    load_images: bool
        Create an Imager object without images. This is useful if you need to
        calculate conjunctions and don't need to download or load unnecessary data.
    colors: str
        Load all three color channels if "rgb", or individual color channels specified
        by "r", "g", "b" (or any combination of them).
    burst: bool
        Sometimes Trex-rgb uses a burst mode with higher resolution.
    imager: :py:meth:`~asilib.imager.Imager`
        Controls what Imager instance to return, asilib.Imager by default. This
        parameter is useful if you need to subclass asilib.Imager.

    Returns
    -------
    :py:meth:`~asilib.imager.Imager`
        The trex Imager instance.

    Examples
    --------
    >>> from datetime import datetime
    >>> 
    >>> import matplotlib.pyplot as plt
    >>> import asilib.map
    >>> import asilib
    >>> from asilib.asi import trex_rgb
    >>> 
    >>> time = datetime(2021, 11, 4, 7, 3, 51)
    >>> location_codes = ['FSMI', 'LUCK', 'RABB', 'PINA', 'GILL']
    >>> asi_list = []
    >>> ax = asilib.map.create_simple_map()
    >>> for location_code in location_codes:
    >>>     asi_list.append(trex_rgb(location_code, time=time, colors='rgb'))
    >>> 
    >>> asis = asilib.Imagers(asi_list)
    >>> asis.plot_map(ax=ax)
    >>> ax.set(title=time)
    >>> plt.tight_layout()
    >>> plt.show()
    """
    if burst == True:
        raise NotImplementedError(
            'Burst mode still needs implementation as it is a different file format')
    if time is not None:
        time = utils.validate_time(time)
    else:
        time_range = utils.validate_time_range(time_range)

    local_rgb_dir = local_base_dir / 'rgb' / 'images' / location_code.lower()

    if load_images:
        # Download and find image data
        file_paths = _get_h5_files(
            'rgb',
            location_code,
            time,
            time_range,
            rgb_base_url,
            local_rgb_dir,
            redownload,
            missing_ok,
        )

        start_times = len(file_paths) * [None]
        end_times = len(file_paths) * [None]
        for i, file_path in enumerate(file_paths):
            date_match = re.search(r'\d{8}_\d{4}', file_path.name)
            start_times[i] = datetime.strptime(
                date_match.group(), '%Y%m%d_%H%M')
            end_times[i] = start_times[i] + timedelta(minutes=1)
        file_info = {
            'path': file_paths,
            'start_time': start_times,
            'end_time': end_times,
            'loader': lambda path: _load_rgb_h5(path),
        }
    else:
        file_info = {
            'path': [],
            'start_time': [],
            'end_time': [],
            'loader': None,
        }

    if time_range is not None:
        file_info['time_range'] = time_range
    else:
        file_info['time'] = time

    # Download and find the appropriate skymap
    if time is not None:
        _time = time
    else:
        _time = time_range[0]
    _skymap = trex_rgb_skymap(location_code, _time, redownload=redownload)
    print(_skymap,  "Skymap")
    print(np.shape(_skymap), 'skymap shape')
    if custom_alt==False:
        alt_index = np.where(_skymap['FULL_MAP_ALTITUDE'] / 1000 == alt)[0]
        assert (
            len(alt_index) == 1
        ), f'{alt} km is not in the valid skymap altitudes: {_skymap["FULL_MAP_ALTITUDE"]/1000} km. If you want a custom altitude with less percision, please use the custom_alt keyword'
        alt_index = alt_index[0]
        lat=_skymap['FULL_MAP_LATITUDE'][alt_index, :, :]
        lon=_skymap['FULL_MAP_LONGITUDE'][alt_index, :, :]
    elif custom_alt =='geodetic':
        lat,lon = asilib.skymap.geodetic_skymap(
            (float(_skymap['SITE_MAP_LATITUDE']), float(_skymap['SITE_MAP_LONGITUDE']), float(_skymap['SITE_MAP_ALTITUDE']) / 1e3),
            _skymap['FULL_AZIMUTH'],
            _skymap['FULL_ELEVATION'],
            alt
            )
    elif custom_alt == 'interp'
        interp_lat = utils.calculate_slope(_skymap['FULL_MAP_LATITUDE'][0, :, :], _skymap['FULL_MAP_LATITUDE'][1, :, :], _skymap['FULL_MAP_ALTITUDE'] / 1000, _skymap['FULL_MAP_ALTITUDE'] / 1000)  #Get the skymap then interp both
        interp_lon = utils.calculate_slope(_skymap['FULL_MAP_LONGITUDE'][0, :, :], _skymap['FULL_MAP_LONGITUDE'][1, :, :], _skymap['FULL_MAP_ALTITUDE'] / 1000 , _skymap['FULL_MAP_ALTITUDE'] / 1000)  #Get the skymap then interp both
        lat = utils.interpolate_matrix(_skymap['FULL_MAP_LATITUDE'][0, :, :], interp_lat,  _skymap['FULL_MAP_ALTITUDE'] / 1000, alt)
        lon = utils.interpolate_matrix(_skymap['FULL_MAP_LONGITUDE'][0, :, :], interp_lon,  _skymap['FULL_MAP_ALTITUDE'] / 1000, alt)

    skymap = {
        'lat': lat,
        'lon': lon,
        'alt': alt,
        'el': _skymap['FULL_ELEVATION'],
        'az': _skymap['FULL_AZIMUTH'],
        'path': _skymap['PATH'],
    }

    meta = {
        'array': 'TREX_RGB',
        'location': location_code.upper(),
        'lat': float(_skymap['SITE_MAP_LATITUDE']),
        'lon': float(_skymap['SITE_MAP_LONGITUDE']),
        'alt': float(_skymap['SITE_MAP_ALTITUDE']) / 1e3,
        'cadence': 3,
        'resolution': (480, 553, 3),
        'colors': colors,
    }
    plot_settings = {'color_norm':'lin'}
    return imager(file_info, meta, skymap, plot_settings=plot_settings)
