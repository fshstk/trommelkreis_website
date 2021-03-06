from django.core.management.base import CommandError
from django.core.files import File as DjangoFile
from django.db.utils import IntegrityError

import os
import json
from datetime import datetime
from mutagen.mp3 import EasyMP3, HeaderNotFoundError

from archive.models import Challenge, Session, Artist, AudioFile
from archive.management.commands._print import PrintIncluded


class Command(PrintIncluded):
    help = """
    Add files from local directory to database.
    All added files/sessions/challenges must not already be in the database,
    or unpredicted behaviour will occur.
    
    Usage:
    ./manage.py addlocal /full/path/to/archive/

    Directory structure must be as follows:
    archive/
        <session slug (generally in "yyyymmdd" form)>/
            sessioninfo.json
            challenge.md
            files/
                <files.mp3>

    sessioninfo.json must include the following keys:
        "session.date" (yyyymmdd, must be identical to directory name)
        "challenge.name"
        "challenge.blurb" (optional but recommended)
        "challenge.copyright" (copyright issues? default: False)

    challenge.md is an optional markdown document containing long-form challenge
    info (saved to challenge.description); may contain HTML/JS.
    """

    def add_arguments(self, parser):
        parser.add_argument("archive_path")

    def handle(self, *args, **options):
        archive_path = options["archive_path"]
        sessionlist = next(os.walk(archive_path))[1]
        sessionlist.sort()

        for dirname in sessionlist:
            self.print("--------------------------------------------")
            self.print("Directory: {}".format(dirname))

            seshpath = os.path.join(archive_path, dirname)
            markdownfile = os.path.join(seshpath, "challenge.md")
            infofile = os.path.join(seshpath, "sessioninfo.json")

            try:
                with open(infofile) as f:
                    seshinfo = json.load(f)
            except FileNotFoundError:
                self.printerror("missing sessioninfo.json")
                continue
            except json.decoder.JSONDecodeError:
                self.printerror("malformed or unreadable sessioninfo.json")
                continue

            try:
                copyflag = seshinfo["challenge.copyright"]
            except KeyError:
                self.printwarning("missing copyright flag. Assuming False.")
                copyflag = False

            try:
                seshdate = datetime.strptime(seshinfo["session.date"], "%Y%m%d")
            except KeyError:
                self.printerror("missing date in sessioninfo.json")
                continue
            except ValueError:
                self.printerror("date in session.info not in yyyymmdd form")
                continue

            try:
                (challenge, challengecreated) = Challenge.objects.get_or_create(
                    name=seshinfo["challenge.name"], copyright_issues=copyflag
                )
            except KeyError:
                self.printerror("missing challenge.name in sessioninfo.json")
                continue
            if challengecreated:
                self.printsuccess("created challenge: {}".format(challenge.name))
            else:
                self.print("Challenge: {}".format(challenge.name))

            (sesh, sessioncreated) = Session.objects.get_or_create(
                challenge=challenge, date=seshdate, slug=dirname,
            )
            if sessioncreated:
                self.printsuccess("created session: {}".format(sesh.slug))
            else:
                self.printnotice("session already exists")

            try:
                sesh.challenge.blurb = seshinfo["challenge.blurb"]
            except KeyError:
                self.printwarning("missing challenge.blurb")

            try:
                with open(markdownfile) as f:
                    sesh.challenge.description = f.read()
            except FileNotFoundError:
                self.printnotice("missing challenge.md")

            sesh.challenge.save()
            sesh.save()

            if "filedirs" in seshinfo:
                filedirs = seshinfo["filedirs"]
            else:
                filedirs = {"files": ""}

            for dirname, subsection in filedirs.items():
                filedir = os.path.join(seshpath, dirname)
                if os.path.isdir(filedir):
                    tracks = next(os.walk(filedir))[2]
                    self.print("Reading directory: {}".format(filedir))
                else:
                    self.printerror("directory does not exist: {}".format(filedir))
                    continue

                for filename in tracks:
                    if not filename.endswith(".mp3"):
                        self.printnotice("unallowed file suffix: {}".format(filename))
                        continue

                    filepath = os.path.join(filedir, filename)

                    try:
                        mp3 = EasyMP3(filepath)
                    except HeaderNotFoundError:
                        self.printerror(
                            "encountered HeaderNotFound error: {}".format(filename)
                        )
                        continue

                    if mp3.info.sketchy:
                        self.printerror("invalid mp3 file: {}".format(filename))
                        continue

                    if "title" in mp3:
                        trackname = mp3["title"][0]
                    else:
                        # Strip off .mp3 suffix:
                        trackname = os.path.splitext(filename)[0]

                    # if AudioFile.objects.filter(session=sesh, name=trackname).exists():
                    #     self.printwarning(
                    #         "file titled '{}' already exists".format(trackname)
                    #     )
                    #     continue

                    track = AudioFile(
                        session=sesh, name=trackname, session_subsection=subsection
                    )

                    with DjangoFile(open(filepath, "rb")) as f:
                        savepath = os.path.join(dirname, filename)
                        track.data.save(savepath, f)
                        self.printsuccess("added {}".format(trackname))

                    if "artist" in mp3:
                        (track.artist, artistcreated) = Artist.objects.get_or_create(
                            name=mp3["artist"][0]
                        )
                        if artistcreated:
                            self.printsuccess("created artist: {}".format(track.artist))

                    track.save()

