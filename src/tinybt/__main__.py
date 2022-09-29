#!/usr/bin/env python3

from argparse import ArgumentParser
from sys import argv

from dht import test_dht
from krpc import test_krpc
from tracker import test_tracker


def main(command_line=argv):
    parser = ArgumentParser()
    parser.add_argument("--test-dht", action="store_true")
    parser.add_argument("--test-krpc", action="store_true")
    parser.add_argument("--test-tracker", action="store_true")
    args = parser.parse_args(command_line)

    if args.test_dht:
        test_tracker()
    elif args.test_tracker:
        test_dht()
    elif args.test_krpc:
        test_krpc()


if __name__ == "__main__":
    main()
