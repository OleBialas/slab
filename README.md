![Package](https://github.com/DrMarc/soundtools/workflows/Python%20package/badge.svg)
[![TestPyPI](https://github.com/DrMarc/soundtools/workflows/TestPyPi/badge.svg)](https://test.pypi.org/project/soundtools/)
[![Documentation Status](https://readthedocs.org/projects/soundtools/badge/?version=latest)](https://soundtools.readthedocs.io/en/latest/?badge=latest)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-brightgreen.svg)](https://github.com/DrMarc/soundtools/graphs/commit-activity)
![PyPI pyversions](https://img.shields.io/badge/python-%3E3.6-blue)
![PyPI license](https://img.shields.io/badge/license-MIT-brightgreen)

**slab**: easy manipulation of sounds and psychoacoustic experiments in Python
======================

**Slab** ('es-lab', or sound laboratory) is an open source project and Python package that makes working with sounds and running psychoacoustic experiments simple, efficient, and fun! For instance, it takes just eight lines of code to run a pure tone audiogram using an adaptive staircase:
```python
    import slab
    stimulus = slab.Sound.tone(frequency=500, duration=0.5) # make a 0.5 sec pure tone of 500 Hz
    stairs = slab.Staircase(start_val=50, n_reversals=10) # set up the adaptive staircase
    for level in stairs: # the staircase object returns a value between 0 and 50 dB for each trial
        stimulus.level = level
        stairs.present_tone_trial(stimulus) # plays the tone and records a keypress (1 for 'heard', 2 for 'not heard')
        stairs.print_trial_info() # optionally print information about the current state of the staircase
    print(stairs.threshold()) # print threshold then done
```

Why slab?
---------
The package aims to lower the entrance barrier for working with sounds in Python and provide easy access to typical operations in psychoacoustics, specifically for students and researchers in the life sciences. The typical BSc or MSc student entering our lab has limited programming and signal processing training and is unable to implement a psychoacoustic experiment from scratch within the time limit of a BSc or MSc thesis. Slab solves this issue by providing easy-to-use building blocks for such experiments. The implementation is well documented and sufficiently simple for curious students to understand. All functions provide sensible defaults and will many cases 'just work' without arguments (vowel = slab.Sound.vowel() gives you a 1-second synthetic vowel 'a' from a male speaker; vowel.spectrogram() plots the spectrogram). This turned out to be useful for teaching and demonstrations. Many students in our lab have now used the package to implement their final projects and exit the lab as proficient Python programmers.

Features
--------
Slab represents sounds as [Numpy](https://www.numpy.org) arrays and provides classes and methods to perform typical sound manipulation tasks and psychoacoustic procedures. The main classes are:

**Signal**: Provides a generic signal object with properties duration, number of samples, sample times, number of channels. Keeps the data in a 'data' property and implements slicing, arithmetic operations, and conversion between sample points and time points.
```python
    sig = slab.Sound.pinknoise(nchannels=2) # make a pink noise
    sig.duration
	out: 1.0
	sig.nsamples
	out: 8000
	sig2 = sig.resample(samplerate=4000) # resample to 4 kHz
	env = sig2.envelope() # returns a new signal containing the lowpass Hilbert envelopes of both channels
	sig.delay(duration=0.0006, channel=0) # delay the first channel by 0.6 ms
```

**Sound**: Inherits from Signal and provides methods for generating, manipulating, displaying, and analysing sound stimuli. Can compute descriptive sound features and apply manipulations to all sounds in a folder.
```python
    vowel = slab.Sound.vowel(vowel='a', duration=.5) # make a 0.5-second synthetic vowel sound
    vowel.ramp() # apply default raised-cosine onset and offset ramps
    vowel.filter(kind='bp', f=[50, 3000]) # apply bandpass filter between 50 and 3000 Hz
    vowel.spectrogram() # plot the spectrogram
    vowel.spectrum(low=100, high=4000, log_power=True) # plot a band-limited spectrum
    vowel.waveform(start=0, end=.1) # plot the waveform
	vowel.write('vowel.wav') # save the sound to a WAV file
	vocoded_vowel = vowel.vocode() # run a vocoding algorithm
	vowel.spectral_feature(feature='centroid') # compute the spectral centroid of the sound in Hz
```

**Binaural**: Inherits from Sound and provides methods for generating and manipulating binaural sounds, including advanced interaural time and intensity manipulation. Binaural sounds have left and a right channel properties.
```python
    sig = slab.Binaural.pinknoise()
	sig.pulse() # make a 2-channel pulsed pink noise
    sig.nchannels
    out: 2
    right_lateralized = sig.itd(duration=600e-6) # add an interaural time difference of 600 microsec, right channel leading
    # apply a linearly increasing or decreasing interaural time difference.
    # This is achieved by sinc interpolation of one channel with a dynamic delay:
    moving = sig.itd_ramp(from_itd=-0.001, to_itd=0.01)
    lateralized = sig.at_azimuth(azimuth=-45) # add frequency- and headsize-dependent ITD and ILD corresponding to a sound at 45 deg
	external = lateralized.externalize() # add a low resolution HRTF filter that results in the percept of an externalized source (i.e. outside of the head), defaults to the KEMAR HRTF recordings, but any HRTF can be supplied
```

**Filter**: Inherits from Signal and provides methods for generating, measuring, and manipulating FIR and FFT filters, filter banks, and transfer functions.
```python
    filt = Filter.rectangular_filter(frequency=15000, kind='hp') # make a highpass filter
	filt.tf() # plot the transfer function
	sig_filt = filt.apply(sig) # apply it to a signal
	# applying a whole filterbank is equally easy:
	fbank = Filter.cos_filterbank(length=sig.nsamples, bandwidth=1/10, low_cutoff=100) # make a cosine filter bank
	fbank.tf() # plot the transfer function of all filters in the bank
	subbands = fbank.apply(sig) # make a multi-channel signal containing the passbands of the filters in the filter bank
	# the subbands could now be manipulated and then combined with the collapse_subbands method
	fbank.filter_bank_center_freqs() # return the centre frequencies of the filters in the filter bank
	fbank = equalizing_filterbank(target, measured) # generates an inverse filter bank for equalizing the differences
	# between measured signals (single- or multi-channel Sound object) and a target signal. Used for equalizing loudspeakers,
	microphones, or speaker arrays.
	fbank.save('equalizing_filters.npy') # saves the filter bank as .npy file.
```

**HRTF**: Inherits from Filter, reads .sofa format HRTFs and provides methods for manipulating, plotting, and applying head-related transfer functions.
```python
    hrtf = slab.HRTF(data='mit_kemar_normal_pinna.sofa') # load HRTF from a sofa file (the standard KEMAR data is included)
    print(hrtf) # print information
    <class 'hrtf.HRTF'> sources 710, elevations 14, samples 710, samplerate 44100.0
    sourceidx = hrtf.cone_sources(20) # select sources on a cone of confusion at 20 deg from midline
    hrtf.plot_sources(sourceidx) # plot the sources in 3D, highlighting the selected sources
    hrtf.plot_tf(sourceidx,ear='left') # plot transfer functions of selected sources in a waterfall plot
	hrtf.diffuse_field_equalization() # apply diffuse field equalization to remove non-spatial components of the HRTF
```

**Psychoacoustics**: A collection of classes for working trial sequences, adaptive staircases, forced-choice procedures, stimulus presentation and response recording from the keyboard and USB button boxes, handling of precomputed stimulus lists, results files, and experiment configuration files.
```python
    # set up an 1up-2down adaptive weighted staircase with dynamic step sizes:
    stairs = slab.Staircase(start_val=10, max_val=40, n_up=1, n_down=2, step_sizes=[3, 1], step_up_factor=1.5)
    for trial in stairs: # draw a value from the staircase; the loop terminates with the staircase
        response = stairs.simulate_response(30) # simulate a response from a participant using a psychometric function
        print(f'trial # {stairs.this_trial_n}: intensity {trial}, response {response}')
        stairs.add_response(response) # logs the response and advances the staircase
		stairs.plot() # updates a plot of the staircase in each trial to keep an eye on the performance of the listener
    stairs.reversal_intensities # returns a list of stimulus values at the reversal points of the staircase
    stairs.threshold() # computes and returns the final threshold
    stairs.save_json('stairs.json') # the staircase object can be saved as a human readable json file

    # for non-adaptive experiments and all other cases where you need a controlled sequence of stimulus values:
    trials = slab.Trialsequence(conditions=5, n_reps=2) # sequence of 5 conditions, repeated twice, without direct repetitions
    trials = slab.Trialsequence(conditions=['red', 'green', 'blue'], kind='infinite') # infinite sequence of color names
    trials = slab.Trialsequence.mmn_sequence(n_trials=60, deviant_freq=0.12) # stimulus sequence for an oddball design
    trials.transitions() # return the array of transition probabilities between all combinations of conditions.
    trials.condition_probabilities() # return a list of frequencies of conditions
    for trial in trials: # use the trials object in a loop to go through the trials
        print(trial) # here you would generate or select a stimulus according to the condition
        trials.present_afc_trial(target, distractor, isi=0.2) # present a 2-alternative forced-choice trial and record the response

    stims = slab.Precomputed(lambda: slab.Sound.pinknoise(), n=10) # make 10 instances of noise as one Sound-like object
    stims = slab.Precomputed([stim1, stim2, stim3, stim4, stim5]) # or use a list of sound objects, or a list comprehension
    stims.play() # play a random instance
    stims.play() # play another one, guaranteed to be different from the previous one
	stims.sequence # the sequence of instances played so far
    stims.save('stims.zip') # save the sounds as zip file
    stims = slab.Precomputed.read('stims.zip') # reloads the file into a Precomputed object
```

The basic functionality of the Signal class and some methods of the Sound class was based on the brian.hears Sound class (now [brain2hears](https://brian2hears.readthedocs.io/en/stable/), an auditory modelling package), but we have significantly expanded the functionality and simplified the architecture to remove recurrent stumbling stones for students without training in object oriented programming (the buffering interface,  direct inheritance from Numpy.array, and the unit package).

Installation
------------
Install slab directly from github (if you have git) by running:
```pip git+https://github.com/DrMarc/soundtools.git```

or from the python package index with pip:
```pip install soundtools```

Documentation
-------------


Contribute
----------

- Issue Tracker: github.com/DrMarc/soundtools/issues
- Source Code: github.com/DrMarc/soundtools

License
-------

The project is licensed under the MIT license.

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)
