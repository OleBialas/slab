from setuptools import setup

with open('README.rst') as f:
    readme = f.read()

setup(name='soundtools',
	version='0.7',
	description='Tools for generating and manipulating digital signals, particularly sounds.',
	long_description=readme,
	url='http://github.com/DrMarc/soundtools.git',
	author='Marc Schoenwiesner',
	author_email='marc.schoenwiesner@gmail.com',
	license='MIT',
	python_requires='>=3.6',
	packages=['slab'],
	package_data={'slab': ['data/mit_kemar_normal_pinna.sofa', 'data/KEMAR_interaural_level_spectrum.npy']},
	include_package_data=True,
	zip_safe=False)
