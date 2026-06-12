import argparse


def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print(Fore.RED + "Missing OPENAI_API_KEY. Please set it in your environment or .env file.")
        sys.exit(1)

    if len(sys.argv) >= 2:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("-e", "--export", nargs="?", const=True, default=False)
        parser.add_argument("pdf_paths", nargs="*")
        parsed_args, _ = parser.parse_known_args(sys.argv[1:])

        for arg in parsed_args.pdf_paths:
            path = Path(arg)
            if not path.exists():
                print(Fore.RED + f"File not found: {arg}")
                sys.exit(1)
            if not path.is_file():
                print(Fore.RED + f"Not a file: {arg}")
                sys.exit(1)
            if not os.access(path, os.R_OK):
                print(Fore.RED + f"File is not readable: {arg}")
                sys.exit(1)

    print(Fore.GREEN + "Setup OK ✓")
