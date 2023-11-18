import click
from k8s import k8s

ALLOWED_PLATFORMS = ['AWS', 'Azure', 'K8s']


def choose_platform(name):
    match name:
        case "K8s":
            k8s()
        case _:
            logging.error(f"selected platform: '{name}' is not supported")


@click.command()
@click.option('--platform', type=click.Choice(ALLOWED_PLATFORMS), required=True, help='Specify a platform.')
def main(platform):
    click.echo(f'Selected platform: {platform}')
    choose_platform(platform)


if __name__ == '__main__':
    main()
