#!/usr/bin/env python
import os
import sys
import re
import stat
import argparse

class PusherCommand(object):
	'''
	decription
		Class used to store data for a command
	members
		(int, string) line:
			The original command string in a tuplet with its line number
		(string) options:
			String of options specified
		(list of string) inputs:
			The input files
		(list of string) outputs:
			The output files
		(boolean) isTarget:
			Checks if command is a target command or generic command
	'''
	def __str__(self):
		return '%d: %s' % self.line
	
	def __init__(self, lineNum, line):
		'''
		description
			Constructor
		args
			(int) lineNum:
				The number of the line passed in
			(string) line
				The command line to be processed
		except
			ValueError
		'''
		self.inputs = []
		self.outputs = []
		self.options = ''
		
		#Validate whether command is valid. If not, raise exception
		if not isValidCommand(line):
			raise ValueError('Error: Invalid syntax on pushfile line: ' + str(lineNum))
		
		self.line = (lineNum, re.sub('\s', '' , line))	
		
		#Check if line is a target, or normal command
		if re.match('^\t:', line):
			self.isTarget = True
			self.inputs.append(self.line[1].replace(':', ''))
			return
		else:
			self.isTarget = False
			
		#Parse out values into correct lists
		line = re.sub('[\s]', '' , line)
		#Options
		if re.search('\|', line):
			remaining, self.options = tuple(line.split('|'))
		else:
			remaining = line
		#Inputs and outputs
		inputsString, outputsString = tuple(remaining.split('=>'))
		
		self.inputs = inputsString.split('+')
		self.outputs= outputsString.split('+')
	
	def hasOption(self, flag):
		'''
		description
			Checks if command uses a certain flag in its options
		args
			(string) flag:
				A single character flag to be checked.
		return
			True if flag is used, False if otherwise
		except
			ValueError
		'''
		if len(flag) != 1:
			raise ValueError('Flag needs to be a single character')
		else:
			return bool(re.search(flag, self.options))
		
	#Getters and setters
	@property
	def line(self):
		'''
		The command string and its line number.
		'''
		return self._line
	@line.getter
	def line(self):
		return self._line
	@line.setter
	def line(self, new):
		self._line = new
		
	@property
	def options(self):
		'''
		String of options specified
		'''
		return self._options
	@options.getter
	def options(self):
		return self._options
	@options.setter
	def options(self, new):
		self._options = new
		
	@property
	def inputs(self):
		'''
		The input files
		'''
		return self._inputs
	@inputs.getter
	def inputs(self):
		return self._inputs
	@inputs.setter
	def inputs(self, new):
		self._inputs = new
		
	@property
	def outputs(self):
		'''
		The output files
		'''
		return self._outputs
	@outputs.getter
	def outputs(self):
		return self._outputs
	@outputs.setter
	def outputs(self, new):
		self._outputs = new
	
	@property
	def isTarget(self):
		'''
		Checks if command is a target command or generic command
		'''
		return self._isTarget
	@isTarget.getter
	def isTarget(self):
		return self._isTarget
	@isTarget.setter
	def isTarget(self, new):
		self._isTarget = new

class Pusher(object):
	'''
	description
		The class in charge of running the push mechanism. Reads in an executes commands
	members
		(dict: string : list of PusherCommand) commands:
			Using target names as keys, returns the list of commands in order under that
			target in execution order.
		(list of string) targets:
			Build target names in read order.
	'''
	
	def __str__(self):
		output = ''
		for target in self.targets:
			output += (target + '\n')
			for command in self.commands[target]:
				output += ('\t' + str(command) + '\n')
		return output
	
	def __init__(self, pushFile):
		'''
		description
			Constructor
		args
			(string) pushFile:
				A file containing the push commands
		except
			ValueError
		'''
		self.commands = {}
		self.targets = []
		pushFile = open(pushFile, 'r')
		#Line number counter
		i = 0
		currentTarget = ''
		for line in pushFile:
			i += 1
			#skip line if comments or whitespace
			if (line == '') or re.match('^[\s]*#', line) or re.match('^\s*$', line):
				continue
			#check if target declaration
			elif re.match('^\w+\s*$', line):
				currentTarget = line.strip()
				self.targets.append(currentTarget)
				self.commands[currentTarget] = []
			#check if it's a command belonging to target
			elif re.match('^\t+', line):
				if currentTarget == '':
					raise ValueError('Error: Invalid syntax on line ' + str(i))
				else:
					self.commands[currentTarget].append(PusherCommand(i, line))
			#Unrecognized syntax
			else:
				raise ValueError('Error: Invalid syntax on line ' + str(i))
		
	def executeTarget(self, target):
		'''
		description
			Executes a target
		args
			(string) target:
				The target to execute
		return
			void
		except
			ValueError
		'''
		if target not in self.targets:
			raise ValueError('Error: Cannot execute target `'+ target +'`; does not exist.')
		for command in self.commands[target]:
			#Check if target or not to choose proper exec function
			if command.isTarget:
				self.executeTarget(command.inputs[0])
			else:
				self.executeCommand(command)
			
	def executeCommand(self, command):
		'''
		description
			Executes a target
		args
			(PusherCommand) command:
				The command to execute
		return
			void
		'''
		inputFiles = []
		outputFiles = []
		outputText = ''
		
		#Prepare files for use
		for filename in command.inputs:
			try:
				inputFiles.append(open(filename, 'r'))
			except IOError as e:
				raise IOError('Error on line ' + str(command.line[0]) + ': ' + e.message + ' Input file not found.')
		for filename in command.outputs:
			try:
				outputFiles.append(open(filename, 'w+'))
			except IOError as e:
				print e
		
		#Begin pasting files together for output.
		for file in inputFiles:
			outputText += file.read() + '\n'
		#Write to output files and close
		for file in outputFiles:
			file.write(outputText)
				
			#If option x is present, make permissions executable
			if command.hasOption('x'):
				fileState = os.stat(file.name)
				os.chmod(file.name, fileState.st_mode | stat.S_IEXEC)
			file.close()
			
		
#Helpers
def isValidCommand(line):
	'''
	description
		Checks whether command line is valid.
	args
		(string) line:
			Line to be passed it for validation
	return
		True if valid command. False if not.
	'''
	pathRE = '[~\w_\\/.-]+'
	pushExpressionRE = pathRE + '([ \t]*\+[ \t]*' + pathRE + ')*'
	pushEquationRE = pushExpressionRE + '[ \t]*=>[ \t]*' + pushExpressionRE
	fullPushCommandRE = pushEquationRE + '([ \t]*\|[ \t]*[a-zA-Z0-9]+)?\w*'
	
	return (re.match('^\t:[\w.-]+$',line) or 
		re.match('^\t' + fullPushCommandRE + '$',line))

def isCommand(line):
	'''
	description
		Checks whether line is a command or target declaration by looking for tabs
	args
		(string) line:
			Line to check
	return
		True if command. False if target declaration.
	'''
	if re.match('^\s', line):
		return True
	else:
		return False

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Push: A simple file pushing utility by Alexander Stein.')
	parser.add_argument('target', nargs='?', default='all', help='The name of the target. Default: `all`')
	parser.add_argument('-f', '--pushfile', default='pushfile', help='Name of the pushfile. Default: `pushfile`')
	
	args = parser.parse_args()
	
	if not os.path.isfile(args.pushfile):
		print 'Push: Error: pushfile `%s` not found.' % args.pushfile 
		exit(-1)
	try:
		pusher = Pusher(args.pushfile)
		pusher.executeTarget(args.target)
	except ValueError as e:
		print '    Push: ' + e.message
		exit(-1)
	except IOError as e:
		print 'Push: ' + e.message
		exit(-1)