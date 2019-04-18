'''
psychoacoustics exports classes for handling psychophysical procedures and
measures, like trial sequences and staircases.
This module uses doctests. Use like so:
python -m doctest psychoacoustics.py
'''
# Staircase
import os
import json
import curses
import collections
import numpy
import matplotlib.pyplot as plt

#TODO: add hearing tests (x-frequency treshold, Bekesy [only TDT], speech-in-noise [ask Annelies])
class Keypress:
	'''
	Wrapper for curses module to simplify getting a single keypress from the terminal.
	Use like this:
	key = Keypress() # hogs the terminal -> use right before getting keypresses
	response = key.get()
	key.stop() # releases the terminal -> use asap after getting keypresses
	'''
	def __init__(self):
		'Locks the terminal in cbreak mode. Use once right before getting keypresses.'
		self.stdscr = curses.initscr()
		curses.noecho()
		curses.cbreak()

	def get(self):
		'Returns a single character.'
		return self.stdscr.getch()

	@staticmethod
	def stop():
		'Releases the terminal. Call asap after getting the keypress.'
		curses.nocbreak()
		curses.echo()
		curses.endwin()

class LoadSaveJson:
	'Mixin to provide JSON loading and saving functions'
	def save_json(self, file_name=None):
		"""
		Serialize the object to the JSON format.
		fileName: string, or None
			the name of the file to create or append. If `None`,
			will not write to a file, but return an in-memory JSON object.
		"""
		#self_copy = copy.deepcopy(self) use if reading the json file sometimes fails
		if (file_name is None) or (file_name == 'stdout'):
			return json.dumps(self.__dict__, indent=2)
		else:
			try:
				with open(file_name, 'w') as f:
					json.dump(self.__dict__, f, indent=2)
					return 1
			except OSError:
				return -1

	def load_json(self, file_name):
		"""
		Read JSON file and deserialize the object into self.__dict__.
		file_name: string, the name of the file to read.
		"""
		with open(file_name, 'r') as f:
			self.__dict__ = json.load(f)


class Trialsequence(collections.abc.Iterator, LoadSaveJson):
	"""Non-adaptive trial sequences
	Parameters:
	conditions: an integer, list, or flat array specifying condition indices,
		or a list of dictionaries with values for each condition index.
		If given an integer x, uses range(x).
	n_reps: number of repeats for all conditions
	name: a text label for the sequence.

	Attributes:
	.n_trials - the total number of trials that will be run
	.n_remaining - the total number of trials remaining
	.this_n - total trials completed so far
	.this_rep_n - which repeat you are currently on
	.this_trial_n - which trial number *within* that repeat
	.this_trial - a dictionary giving the parameters of the current trial
	.finished - True/False for have we finished yet
"""
	def __init__(self, conditions=2, n_reps=1, trials=[], name=''):
		self.name = name
		self.n_reps = int(n_reps)
		self.conditions = conditions
		if isinstance(conditions, str) and os.path.isfile(conditions):
			self.load_json(conditions) # import entire object from file
		elif isinstance(conditions, int):
			self.conditions = list(range(conditions))
		else:
			self.conditions = conditions
		self.n_conds = len(self.conditions)
		self.this_rep_n = 0  # records which repetition or pass we are on
		self.this_trial_n = -1  # records trial number within this repetition
		self.this_n = -1
		self.this_trial = []
		self.finished = False
		# generate stimulus sequence
		self.trials = trials
		if not trials:
			self._create_simple_sequence()
		self.n_trials = len(self.trials)
		self.n_remaining = self.n_trials  # subtract 1 each trial


	def __repr__(self):
		return self.save_json()

	def __str__(self):
		return f'Trialsequence, trials {self.n_trials}, remaining {self.n_remaining}, current condition {self.this_trial}'

	def __next__(self):
		"""Advances to next trial and returns it.
		Updates attributes; this_trial, this_trial_n
		If the trials have ended this method will raise a StopIteration error.
		trials = Trialsequence(.......)
			for eachTrial in trials:  # automatically stops when done
		"""
		self.this_trial_n += 1  # number of trial this pass
		self.this_n += 1  # number of trial in total
		self.n_remaining -= 1
		if self.this_trial_n >= self.n_conds and (self.n_reps > 1):
			self.this_trial_n = 0 # start a new repetition
			self.this_rep_n += 1
		if self.this_n >= len(self.trials): # all trials complete
			self.this_trial = []
			self.finished = True
		if self.finished:
			raise StopIteration
		self.this_trial = self.conditions[self.trials[self.this_n]] # fetch the trial info
		return self.this_trial

	def _create_simple_sequence(self):
		'''Create a sequence of n_conds x n_reps trials, where each repetitions
		contains all conditions in random order, and no condition is directly
		repeated across repetitions.'''
		permute = self.conditions
		for rep in range(self.n_reps):
			numpy.random.shuffle(permute)
			if rep == 0: # first repetition
				self.trials.extend(permute)
			else:
				while self.trials[-1] == permute[0]:
					permute = self.conditions
					numpy.random.shuffle(permute)
				self.trials.extend(permute)

	def get_future_trial(self, n=1):
		"""Returns the condition for n trials into the future or past,
		without advancing the trials. A negative n returns a previous (past)
		trial. Returns 'None' if attempting to go beyond the last trial.
		"""
		if n > self.n_remaining or self.this_n + n < 0:
			return None
		return self.trials[self.this_n + n]

	def transitions(self):
		'Return array (n_conds x n_conds) of transition probabilities.'
		transitions = numpy.zeros((self.n_conds, self.n_conds))
		for i, j in zip(self.trials, self.trials[1:]):
			transitions[i, j] += 1
		return transitions

	def condition_probabilities(self):
		'Return list of frequencies of conditions in the order listed in .conditions'
		probs = []
		for i in range(self.n_conds):
			num = self.trials.count(i)
			num /= self.n_trials
			probs.append(num)
		return probs

	def plot(self):
		'Plot the trial sequence as scatter plot.'
		plt.plot(self.trials)
		plt.xlabel('Trials')
		plt.ylabel('Condition index')
		plt.show()

	@staticmethod
	def mmn_sequence(n_trials, deviant_freq=0.12):
		'''Returns a  MMN experiment: 2 different stimuli (conditions),
		between two deviants at least 3 standards
		n_trials: number of trials to return
		deviant_freq: frequency of deviants (*0.12*, max. 0.25)
		'''
		n_partials = int(numpy.ceil((2 / deviant_freq) - 7))
		reps = int(numpy.ceil(n_trials/n_partials))
		partials = []
		for i in range(n_partials):
			partials.append([0] * (3+i) + [1])
		idx = list(range(n_partials)) * reps
		numpy.random.shuffle(idx) # randomize order
		trials = [] # make the trial sequence by putting possibilities together
		for i in idx:
			trials.extend(partials[i])
		trials = trials[:n_trials] # cut the list to the requested numner of trials
		return Trialsequence(conditions=2, n_reps=1, trials=trials)


class Staircase(collections.abc.Iterator):
	#TODO: add Kaernbach1991 weighted up-down method?
	#TODO: add QUEST or Bayesian estimation?
	#TODO: fit psychometric function
	"""Class to handle smoothly the selection of the next trial
	and report current values etc.
	Calls to next() will fetch the next object given to this
	handler, according to the method specified.
	The staircase will terminate when *n_trials* AND *n_reversals* have
	been exceeded. If *step_sizes* was an array and has been exceeded
	before n_trials is exceeded then the staircase will continue
	to reverse.
	*n_up* and *n_down* are always considered as 1 until the first reversal
	is reached. The values entered as arguments are then used.
	Example:
	>>> stairs = Staircase(start_val=50, n_reversals=10, step_type='lin',\
			step_sizes=[4,2], min_val=10, max_val=60, n_up=1, n_down=1, n_trials=10)
	>>> print(stairs)
	<class 'psychoacoustics.Staircase'> 1up1down, trial -1, 0 reversals of 10
	>>> for trial in stairs:
	... 	response = stairs.simulate_response(30)
	... 	stairs.add_response(response)
	>>> print(f'reversals: {stairs.reversal_intensities}')
	reversals: [26, 30, 28, 30, 28, 30, 28, 30, 28, 30]
	>>> print(f'mean of final 6 reversals: {stairs.threshold()}')
	mean of final 6 reversals: 28.982753492378876
	"""
	def __init__(self, start_val, n_reversals=None, step_sizes=4, n_trials=0, n_up=1,
		n_down=2, step_type='db', min_val=None, max_val=None, name=''):
		"""
		:Parameters:
			name:
				A text label.
			start_val:
				The initial value for the staircase.
			n_reversals:
				The minimum number of reversals permitted.
				If `step_sizes` is a list, but the minimum number of
				reversals to perform, `n_reversals`, is less than the
				length of this list, PsychoPy will automatically increase
				the minimum number of reversals and emit a warning.
			step_sizes:
				The size of steps as a single value or a list (or array).
				For a single value the step size is fixed. For an array or
				list the step size will progress to the next entry
				at each reversal.
			n_trials:
				The minimum number of trials to be conducted. If the
				staircase has not reached the required number of reversals
				then it will continue.
			n_up:
				The number of 'incorrect' (or 0) responses before the
				staircase level increases.
			n_down:
				The number of 'correct' (or 1) responses before the
				staircase level decreases.
			step_type: *'db'*, 'lin', 'log'
				The type of steps that should be taken each time. 'lin'
				will simply add or subtract that amount each step, 'db'
				and 'log' will step by a certain number of decibels or
				log units (note that this will prevent your value ever
				reaching zero or less)
			min_val: *None*, or a number
				The smallest legal value for the staircase, which can be
				used to prevent it reaching impossible contrast values,
				for instance.
			max_val: *None*, or a number
				The largest legal value for the staircase, which can be
				used to prevent it reaching impossible contrast values,
				for instance.
		"""
		self.name = name
		self.start_val = start_val
		self.n_up = n_up
		self.n_down = n_down
		self.step_type = step_type
		try:
			self.step_sizes = list(step_sizes)
		except TypeError:
			self.step_sizes = [step_sizes]
		self._variable_step = True if len(self.step_sizes) > 1 else False
		self.step_size_current = self.step_sizes[0]
		if n_reversals is None:
			self.n_reversals = len(self.step_sizes)
		elif len(self.step_sizes) > n_reversals:
			print(f'Increasing number of minimum required reversals to the number of step sizes, {len(self.step_sizes)}')
			self.n_reversals = len(self.step_sizes)
		else:
			self.n_reversals = n_reversals
		self.n_trials = n_trials
		self.finished = False
		self.this_trial_n = -1
		self.data = []
		self.intensities = []
		self.reversal_points = []
		self.reversal_intensities = []
		self.current_direction = 'down'
		self.correct_counter = 0
		self._next_intensity = self.start_val
		self.min_val = min_val
		self.max_val = max_val
		self.pf_intensities = None # psychometric function, auto set when finished
		self.pf_percent_correct = None # psychometric function, auto set when finished
		self.pf_responses_per_intensity = None # psychometric function, auto set when finished

	def __next__(self):
		"""Advances to next trial and returns it.
		Updates attributes; `this_trial`, `this_trial_n` and `thisIndex`.
		If the trials have ended, calling this method will raise a
		StopIteration error. This can be handled with code such as::
			staircase = Staircase(.......)
			for eachTrial in staircase:  # automatically stops when done
				# do stuff
		"""
		if not self.finished:
			self.this_trial_n += 1 # update pointer for next trial
			self.intensities.append(self._next_intensity)
			return self._next_intensity
		else:
			self._psychometric_function() # tally responses to create a psychomeric function
			raise StopIteration

	def __str__(self):
		return f'{type(self)} {self.n_up}up{self.n_down}down, trial {self.this_trial_n}, {len(self.reversal_intensities)} reversals of {self.n_reversals}'

	def add_response(self, result, intensity=None):
		"""Add a True or 1 to indicate a correct/detected trial
		or False or 0 to indicate an incorrect/missed trial.
		This is essential to advance the staircase to a new intensity level.
		Supplying an `intensity` value indicates that you did not use
		the recommended intensity in your last trial and the staircase will
		replace its recorded value with the one supplied.
		"""
		result = bool(result)
		self.data.append(result)
		if intensity != None:
			self.intensities.pop()
			self.intensities.append(intensity)
		if result: # correct response
			if len(self.data) > 1 and self.data[-2] == result:
				self.correct_counter += 1 # increment if on a run
			else:
				self.correct_counter = 1 # or reset
		else: # incorrect response
			if len(self.data) > 1 and self.data[-2] == result:
				self.correct_counter -= 1 # decrement if on a run
			else:
				self.correct_counter = -1 # or reset
		self.calculatenext_intensity()

	def calculatenext_intensity(self):
		'Based on current intensity, counter of correct responses, and current direction.'
		if not self.reversal_intensities: # no reversals yet
			if self.data[-1] is True:  # last answer correct
				reversal = bool(self.current_direction == 'up') # got it right
				self.current_direction = 'down'
			else: # got it wrong
				reversal = bool(self.current_direction == 'down')
				self.current_direction = 'up'
		elif self.correct_counter >= self.n_down: # n right, time to go down!
			reversal = bool(self.current_direction != 'down')
			self.current_direction = 'down'
		elif self.correct_counter <= -self.n_up: # n wrong, time to go up!
			reversal = bool(self.current_direction != 'up')
			self.current_direction = 'up'
		else: # same as previous trial
			reversal = False
		if reversal: # add reversal info
			self.reversal_points.append(self.this_trial_n)
			self.reversal_intensities.append(self.intensities[-1])
		if (len(self.reversal_intensities) >= self.n_reversals and len(self.intensities) >= self.n_trials):
			self.finished = True # we're done
		if reversal and self._variable_step: # new step size if necessary
			if len(self.reversal_intensities) >= len(self.step_sizes): # if beyond the list of step sizes, use the last one
				self.step_size_current = self.step_sizes[-1]
			else:
				_sz = len(self.reversal_intensities)
				self.step_size_current = self.step_sizes[_sz]
		if not self.reversal_intensities:
			if self.data[-1] == 1:
				self._intensity_dec()
			else:
				self._intensity_inc()
		elif self.correct_counter >= self.n_down:
			self._intensity_dec() # n right, so going down
		elif self.correct_counter <= -self.n_up:
			self._intensity_inc() # n wrong, so going up

	def _intensity_inc(self):
		'increment the current intensity and reset counter'
		if self.step_type == 'db':
			self._next_intensity *= 10.0**(self.step_size_current/20.0)
		elif self.step_type == 'log':
			self._next_intensity *= 10.0**self.step_size_current
		elif self.step_type == 'lin':
			self._next_intensity += self.step_size_current
		if (self.max_val is not None) and (self._next_intensity > self.max_val):
			self._next_intensity = self.max_val # check we haven't gone out of the legal range
		self.correct_counter = 0

	def _intensity_dec(self):
		'decrement the current intensity and reset counter'
		if self.step_type == 'db':
			self._next_intensity /= 10.0**(self.step_size_current/20.0)
		if self.step_type == 'log':
			self._next_intensity /= 10.0**self.step_size_current
		elif self.step_type == 'lin':
			self._next_intensity -= self.step_size_current
		self.correct_counter = 0
		if (self.min_val is not None) and (self._next_intensity < self.min_val):
			self._next_intensity = self.min_val # check we haven't gone out of the legal range

	def simulate_response(self,thresh):
		# TODO: use psychometric function (Weibull?) to generate responses
		'Return a simulated response dependent on thresh and self.'
		return self._next_intensity >= thresh

	def threshold(self,n=6,method='geometric'):
		'Returns the average (geometric by default) reversal to calculate the threshold.'
		if self.finished:
			if n > self.n_reversals:
				n = self.n_reversals
			if method == 'geometric':
				return numpy.exp(numpy.mean(numpy.log(self.reversal_intensities[-n:])))
			else:
				return numpy.mean(self.reversal_intensities[-n:])

	def save_csv(self, fileName):
		'Write a text file with the data.'
		if self.this_trial_n < 1:
			return -1 # no trials to save
		with open(fileName, 'w') as f:
			raw_intens = str(self.intensities)
			raw_intens = raw_intens.replace('[', '').replace(']', '')
			f.write(raw_intens)
			f.write('\n')
			responses = str(numpy.multiply(self.data, 1)) # convert to 0 / 1
			responses = responses.replace('[', '').replace(']', '')
			responses = responses.replace(' ', ', ')
			f.write(responses)

	def plot(self, plot_pf=True):
		'Plot the staircase (and the psychometric function if plot_pf=True and the staicase is finished).'
		x = numpy.arange(self.this_trial_n + 1)
		y = numpy.array(self.intensities)
		responses = numpy.array(self.data)
		if self.pf_intensities and plot_pf:
			_,(ax1,ax2) = plt.subplots(1, 2, sharey='row', gridspec_kw={'width_ratios':[2, 1], 'wspace':0.1}) # prepare a second panel for the pf plot
			#fig.subplots_adjust(wspace=0)
		else:
			_, ax1 = plt.subplots() # need just one panel
		ax1.plot(x, y)
		ax1.set_xlim(numpy.min(x), numpy.max(x))
		ax1.set_ylim(numpy.min(y), numpy.max(y))
		ax1.scatter(x[responses], y[responses], color='green') # plot green dots at correct/yes responses
		ax1.scatter(x[~responses], y[~responses], color='red') # plot red dots at correct/yes responses
		ax1.set_ylabel('Dependent variable')
		ax1.set_xlabel('Trial')
		ax1.set_title('Staircase')
		if self.finished:
			ax1.hlines(self.threshold(), min(x), max(x), 'r')
		if 'ax2' in locals(): # if ax2 was created above, plot into it
			ax2.plot(self.pf_percent_correct, self.pf_intensities)
			point_sizes = self.pf_responses_per_intensity * 5 # 5 pixels per trial at each point
			ax2.scatter(self.pf_percent_correct, self.pf_intensities, s=point_sizes)
			ax2.set_xlabel('Hit rate')
			ax2.set_title('Psychometric\nfunction')
		plt.show()

	def _psychometric_function(self):
		"""Create a psychometric function by binning data from a staircase
		procedure. Called automatically when staircase is finished. Sets
		pf_intensites
				a numpy array of intensity values (where each is the center
				of an intensity bin)
		pf_percent_correct
				a numpy array of mean percent correct in each bin
		pf_responses_per_intensity
				a numpy array of number of responses contributing to each mean
		"""
		intensities = numpy.array(self.intensities)
		responses = numpy.array(self.data)
		binned_resp = []
		binned_intens = []
		n_points = []
		intensities = numpy.round(intensities, decimals=8)
		unique_intens = numpy.unique(intensities)
		for this_intens in unique_intens:
			these_resps = responses[intensities == this_intens]
			binned_intens.append(this_intens)
			binned_resp.append(numpy.mean(these_resps))
			n_points.append(len(these_resps))
		self.pf_intensities = binned_intens
		self.pf_percent_correct = binned_resp
		self.pf_responses_per_intensity = n_points

if __name__ == '__main__':
	# Demonstration
	tr = Trialsequence(conditions=5, n_reps=2, name='test')
	stairs = Staircase(start_val=50, n_reversals=10, step_type='lin', step_sizes=
				[8, 4, 4, 2, 2, 1],  # reduce step size every two reversals
				min_val=0, max_val=60, n_up=1, n_down=1, n_trials=15)
	for trial in stairs:
		response = stairs.simulate_response(30)
		print(f'trial # {stairs.this_trial_n}: intensity {trial}, response {response}')
		stairs.add_response(response)
	print(f'reversals: {stairs.reversal_intensities}')
	print(f'mean of final 6 reversals: {stairs.threshold()}')
	#stairs.save_json('stairs.json')
	stairs.plot()