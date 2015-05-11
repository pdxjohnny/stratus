"""
Stratus

Facilitates connections



"""

import stratus
import argparse


ARG_PARSER = False

def server_start():
	pass

def client_start():
	pass

def arg_setup():
	global ARG_PARSER
	ARG_PARSER = argparse.ArgumentParser(description=stratus.__description__)
	ARG_PARSER.add_argument("--port", type=int, help="Port to host stratus server")
	ARG_PARSER.add_argument('--version', action='version', \
		version=u'%(prog)s ' + unicode(stratus.__version__) )
	return ARG_PARSER.parse_args()

def main():
	print stratus.__logo__
	args = arg_setup()
	return 0

if __name__ == '__main__':
	main()
