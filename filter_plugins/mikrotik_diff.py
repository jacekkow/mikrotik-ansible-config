#!/usr/bin/env python3

class MikrotikDiffModule(object):

	noescape_allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#%&*+,-./:<>@]^_|}~'
	noescape_string = noescape_allowed + ' \'();=?[`{'

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
	def mikrotik_output_attributes(cls, data, subset = None):
		result = ''
		for attr, value in data.items():
			if attr == '_':
				continue
			if subset is None or attr in subset:
				result += ' ' + attr + '=' + cls.mikrotik_escape(value)
		return result

	remove_attrs_special_negate = set((
		'egress-rate',
		'forced-mac-address',
		'ingress-rate',
	))
	remove_attrs_special_value = {
		'disabled': 'no',
		'frame-types': 'admit-all',
		'limit-broadcasts': 'yes',
		'limit-unknown-multicasts': 'no',
		'limit-unknown-unicasts': 'no',
		'storm-rate': '100',
	}

	@classmethod
	def mikrotik_remove_attributes(cls, attrs):
		result = ''
		for attr in attrs:
			if attr in cls.remove_attrs_special_negate:
				result += ' !' + attr
			elif attr in cls.remove_attrs_special_value:
				result += ' ' + attr + '=' + cls.remove_attrs_special_value[attr]
			else:
				result += ' ' + attr + '=""'
		return result

	@classmethod
	def mikrotik_diff_object(cls, prefix, unique_attribute, unique_value, current, desired):
		if unique_attribute == '_':
			find_part = ' ' + cls.mikrotik_escape(unique_value)
		else:
			find_part = ' [ find ' + unique_attribute + '=' + cls.mikrotik_escape(unique_value) + ' ]'

		if desired is None:
			return prefix + ' remove' + find_part

		if current is None:
			if unique_attribute != '_':
				return prefix + ' add ' + unique_attribute + '=' + cls.mikrotik_escape(unique_value) + cls.mikrotik_output_attributes(desired)
			current = {}

		remove_attrs_part = cls.mikrotik_remove_attributes(current.keys() - desired.keys())
		return prefix + ' set' + find_part + remove_attrs_part + cls.mikrotik_output_attributes(desired, [key for key in desired if key not in current or current[key] != desired[key]])

	@classmethod
	def mikrotik_diff(cls, current, desired):
		if current['prefix'] != desired['prefix']:
			raise Exception('Incompatibile object prefix: {} != {}'.format(current['prefix'], desired['prefix']))
		if current['unique_attribute'] != desired['unique_attribute']:
			raise Exception('Incompatibile unique attribute: {} != {}'.format(current['unique_attribute'], desired['unique_attribute']))

		prefix = current['prefix']
		unique_attribute = current['unique_attribute']

		current_keys = set(current['data'].keys())
		desired_keys = set(desired['data'].keys())

		add = desired_keys - current_keys
		remove = current_keys - desired_keys
		change = current_keys & desired_keys

		for key_change in list(change):
			if current['data'][key_change] == desired['data'][key_change]:
				change.remove(key_change)

		rename = []
		for key_add in list(add):
			for key_remove in list(remove):
				if desired['data'][key_add] == current['data'][key_remove]:
					rename.append((key_remove, key_add))
					add.remove(key_add)
					remove.remove(key_remove)
					break

		result = []
		for key_remove in remove:
			result.append(cls.mikrotik_diff_object(prefix, unique_attribute, key_remove, None, None))
		for key_change in change:
			result.append(cls.mikrotik_diff_object(prefix, unique_attribute, key_change, current['data'][key_change], desired['data'][key_change]))
		for key_add in add:
			result.append(cls.mikrotik_diff_object(prefix, unique_attribute, key_add, None, desired['data'][key_add]))
		for key_rename_from, key_rename_to in rename:
			result.append(cls.mikrotik_diff_object(prefix, unique_attribute, key_rename_from, {}, {unique_attribute: key_rename_to}))
		return result

class FilterModule(object):
	def filters(self):
		return {
			'mikrotik_diff': MikrotikDiffModule.mikrotik_diff,
		}


def test_diff(module):
	from mikrotik_parse import MikrotikParseModule as parse
	inputs = [
		('/ add name=test', '/ add name=test2', ['/ set [ find name=test ] name=test2']),
		('', '/ add name=test', ['/ add name=test']),
		('/ add name=test', '', ['/ remove [ find name=test ]']),
	]
	inputs_set = [
		('', '/ set a name=test2', ['/ set a name=test2']),
		('/ set a name=test2', '', ['/ remove a']),
		('/ set a name=test2', '/ set a test=test2', ['/ set a name="" test=test2']),
	]
	for source, destination, expected in inputs:
		source_parsed = parse.mikrotik_parse(source, '/', 'name')
		destination_parsed = parse.mikrotik_parse(destination, '/', 'name')
		result = module.mikrotik_diff(source_parsed, destination_parsed)
		print('RESULT: {}'.format(result))
		print('EXPECT: {}'.format(expected))
		assert result == expected
	for source, destination, expected in inputs_set:
		source_parsed = parse.mikrotik_parse(source, '/', '_')
		destination_parsed = parse.mikrotik_parse(destination, '/', '_')
		result = module.mikrotik_diff(source_parsed, destination_parsed)
		print('RESULT: {}'.format(result))
		print('EXPECT: {}'.format(expected))
		assert result == expected

if __name__ == '__main__':
	module = MikrotikDiffModule
	test_diff(module)
