from octoviz.common import create_directory
from octoviz.config import configuration
    
def cli():
    create_directory('')  # Create the OctoViz directory if it does not exist

    args = configuration().parse_args()

    args.func(args)


if __name__ == "__main__":
    cli()
    