import os
import time
import traceback

from airplay import AirPlay

import click


def get_airplay_device(hostport):
    if hostport is not None:
        try:
            (host, port) = hostport.split(':', 1)
            port = int(port)
        except ValueError:
            host = hostport
            port = 7000

        return AirPlay(host, port)

    devices = AirPlay.find(fast=True)

    if len(devices) == 0:
        raise RuntimeError('No AirPlay devices were found.  Use --device to manually specify an device.')
    elif len(devices) == 1:
        return devices[0]
    elif len(devices) > 1:
        error = "Multiple AirPlay devices were found.  Use --device to select a specific one.\n\n"
        error += "Available AirPlay devices:\n"
        error += "--------------------\n"
        for dd in devices:
            error += "\t* {0}: {1}:{2}\n".format(dd.name, dd.host, dd.port)

        raise RuntimeError(error)


def humanize_seconds(secs):
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)

    return "%02d:%02d:%02d" % (h, m, s)


@click.group()
def cli():
    pass


@cli.command()
def discover(path):
    """Discover AirPlay devices in connected network"""
    click.echo("hello, discover!")


@cli.command()
@click.argument('path', metavar='<path/url>')
def photo(path):
    """AirPlay a photo"""
    click.echo("hello, photo!")


@cli.command()
@click.argument('path', metavar='<path/url>')
@click.option('-p', '--pos', '--position', metavar="<position>", default=0, type=float)
@click.option('-d', '--dev', '--device', metavar="<host/ip>[:<port>]")
def video(path, position, device):
    """AirPlay a video"""
    # click.echo("yes")
    # if device:
    #     click.echo("device:%s" % device)
    #connect to the AirPlay device we want to control
    try:
        ap = get_airplay_device(device)
    except (ValueError, RuntimeError) as exc:
        traceback.print_exc()

    duration = 0
    state = 'loading'

    # if the url is on our local disk, then we need to spin up a server to start it
    if os.path.exists(path):
        path = ap.serve(path)

    # play what they asked
    ap.play(path, position)

    # stay in this loop until we exit
    with click.progressbar(length=100, show_eta=False) as bar:
        try:
            while True:
                for ev in ap.events(block=False):
                    newstate = ev.get('state', None)

                    if newstate is None:
                        continue

                    if newstate == 'playing':
                        duration = ev.get('duration')
                        position = ev.get('position')

                    state = newstate

                if state == 'stopped':
                    raise KeyboardInterrupt

                bar.label = state.capitalize()

                if state == 'playing':
                    info = ap.scrub()
                    duration = info['duration']
                    position = info['position']

                if state in ['playing', 'paused']:
                    bar.label += ': {0} / {1}'.format(
                        humanize_seconds(position),
                        humanize_seconds(duration)
                    )
                    try:
                        bar.pos = int((position / duration) * 100)
                    except ZeroDivisionError:
                        bar.pos = 0

                bar.label = bar.label.ljust(28)
                bar.render_progress()

                time.sleep(.5)

        except KeyboardInterrupt:
            ap = None
            raise SystemExit


if __name__ == '__main__':
    cli()
