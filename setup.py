#!/usr/bin/env python
"""Setup script for the Grid LOFAR Tools (GRID_LRT) python module
"""
#from distutils.core import setup
from setuptools import setup
import GRID_LRT
 
setup(name='GRID_LRT',
      packages=['GRID_LRT', 'GRID_LRT/staging', 'GRID_LRT/application','GRID_LRT/storage', 'GRID_LRT/auth'],
      version=GRID_LRT.__version__,
      setup_requires=[],
      tests_require=[
          'pytest'
          ],
      install_requires=[
          'retrying',
          'cloudant',
          'humanfriendly' 
          ],
      include_package_data=True,
      data_files=[("GRID_LRT/data/config",
                   ["GRID_LRT/data/config/steps/cal_pref3.json",
                    "GRID_LRT/data/config/steps/targ1_pref3.json",
                    "GRID_LRT/data/config/steps/targ2_pref3.json",
                    "GRID_LRT/data/config/steps/pref_targ2.cfg"]),
                  ("GRID_LRT/data/launchers/",
                   ["GRID_LRT/data/launchers/run_remote_sandbox.sh"])
                 ],
      description='GRID LOFAR Reduction Tools',
      long_description="Software that encapsulates LOFAR processing"
      "and allows the use of High Throughput Distributed processing available"
      "at SURFsara and other European Grid Initiative locations.",
      author='Alexandar Mechev',
      author_email='apmechev+LOFAR@gmail.com',
      url='https://www.github.com/apmechev/GRID_LRT/',
      download_url='https://github.com/apmechev/GRID_LRT/archive/v{}.tar.gz'.format(GRID_LRT.__version__),
      keywords=['surfsara', 'distributed-computing', 'LOFAR'],
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Science/Research',
                   "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                   "Natural Language :: English",
                   "Topic :: Scientific/Engineering :: Astronomy",
                   "Topic :: System :: Distributed Computing", 
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4', 
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6',
                   'Programming Language :: Python :: 3.7']
     )

