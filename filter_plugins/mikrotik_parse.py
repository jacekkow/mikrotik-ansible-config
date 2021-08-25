#!/usr/bin/env python3

import re

class MikrotikParseModule(object):
	@staticmethod
	def parse_lines(data):
		result = []
		for line in data.splitlines():
			if line == '' or line.startswith('#'):
				continue
			if line.startswith(' '):
				if not result[-1].endswith('\\'):
					raise Exception('Line continuation without backslash: {}'.format(line))
				result[-1] = result[-1][0:-1] + line.lstrip(' ')
			else:
				result.append(line)
		return result

	pattern_param = re.compile(r'^(?P<name>[a-z-]+)(=((?P<value_quoted>"([^\\"]+|\\["\\nrt$?_abfv]|\\[0-9A-F][0-9A-F])*")|(?P<value_raw>[^\\" ]+)))?\s*')
	pattern_replace = re.compile(r'\\["\\nrt$?_abfv]|\\[0-9A-F][0-9A-F]')

	@staticmethod
	def parse_replace(match):
		match = match[0][1:]
		if match in ('\\', '"', '$', '?'):
			return match
		elif match in '_':
			return ' '
		elif match in 'n':
			return '\n'
		elif match == 'r':
			return '\r'
		elif match == 't':
			return '\t'
		elif match == 'a':
			return '\a'
		elif match == 'b':
			return '\b'
		elif match == 'f':
			return '\f'
		elif match == 'v':
			return '\v'
		else:
			return chr(int(match, 16))

	noescape_allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#%&*+,-./:<>@]^_|}~'
	noescape_string = noescape_allowed + ' \'();=?[`{'

	@classmethod
	def mikrotik_unescape(cls, string):
		if string.startswith('"'):
			if not string.endswith('"'):
				raise Exception('Invalid Mikrotik string: {}'.format(string))
			return cls.pattern_replace.sub(cls.parse_replace, string[1:-1])
		else:
			print(string[0])
			if string.rstrip(cls.noescape_allowed) != '':
				raise Exception('Unknown raw character in string: {}'.format(string))
			return string

	@classmethod
	def mikrotik_escape(cls, string):
		if string == '':
			return '""'
		if string.rstrip(cls.noescape_allowed) == '':
			return string
		result = '"'
		for letter in string:
			if letter in cls.noescape_string:
				result += letter
			elif letter in '"$?\\':
				result += '\\' + letter
			elif letter == '\n':
				result += '\\n'
			elif letter == '\r':
				result += '\\r'
			elif letter == '\a':
				result += '\\a'
			elif letter == '\b':
				result += '\\b'
			elif letter == '\f':
				result += '\\f'
			elif letter == '\v':
				result += '\\v'
			else:
				result += '\\%02x' % ord(letter)
		result += '"'
		return result

	@classmethod
	def parse_pattern_params(cls, pattern_params):
		result = {}
		match = cls.pattern_param.match(pattern_params)
		while match != None:
			if match['value_quoted'] is not None:
				value = cls.mikrotik_unescape(match['value_quoted'])
			else:
				value = match['value_raw']
			result[match['name']] = value

			pattern_params = pattern_params[len(match[0]):]
			match = cls.pattern_param.match(pattern_params)
		if pattern_params != '':
			raise Exception('Could not parse parameter {}'.format(pattern_params))
		return result

	@classmethod
	def mikrotik_parse(cls, data, prefix, unique_attribute='name'):
		result = {
			'prefix': prefix,
			'unique_attribute': unique_attribute,
			'data': {},
		}
		for line in cls.parse_lines(data):
			if not line.startswith(prefix):
				raise Exception('Line did not start with prefix: {}'.format(line))
			command, line_split = line[len(prefix):].lstrip(' ').split(' ', 1)

			if command != 'add' and command != 'set':
				raise Exception('Only add and set commands are supported by parser, not {}'.format(command))

			if command == 'set':
				target, line_split = line_split.lstrip(' ').split(' ', 1)

			params = cls.parse_pattern_params(line_split)
			if command == 'set':
				params['_'] = target
			if unique_attribute not in params:
				raise Exception('Line is missing unique attribute {}: {}'.format(unique_attribute, line))
			name = params[unique_attribute]
			if name in result['data']:
				raise Exception('Attribute {} is not unique'.format(unique_attribute))
			del params[unique_attribute]
			result['data'][name] = params
		return result

	@classmethod
	def mikrotik_set_prefix(parsed, prefix):
		parsed['unique_attribute'] = prefix

class FilterModule(object):
	def filters(self):
		return {
			'mikrotik_escape': MikrotikParseModule.mikrotik_escape,
			'mikrotik_parse': MikrotikParseModule.mikrotik_parse,
			'mikrotik_set_prefix': MikrotikParseModule.mikrotik_set_prefix,
		}

def test_unescape(module):
	inputs = {
		r'"\\\n"': '\\\n',
		'"\$\$\$"': '$$$',
		'"?\$%^"': '?$%^',
	}
	for inp, exp in inputs.items():
		result = module.mikrotik_unescape(inp)
		assert result == exp
		back = module.mikrotik_escape(exp)
		assert back == inp

def test_parse(module):
	inputs = {
		'/ add name=test a="te\\"st \\\n    \\n" b c=d': {
			'a': 'te"st \n',
			'b': None,
			'c': 'd',
		},
		'/ add name=test a="te\\\\"': {
			'a': 'te\\',
		},
	}
	inputs_set = {
		'/ set test a=b': {
			'a': 'b',
		},
	}
	for example, expected_result in inputs.items():
		result = module.mikrotik_parse(example, '/', 'name')
		assert result['data']['test'] == expected_result
	for example, expected_result in inputs_set.items():
		result = module.mikrotik_parse(example, '/', '_')
		assert result['data']['test'] == expected_result

if __name__ == '__main__':
	module = MikrotikParseModule
	test_unescape(module)
	test_parse(module)
