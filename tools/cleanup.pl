#!/usr/bin/perl

# Edited tracks are re-downloaded with new date and same id
# so with --add-date you end up with several files.
# Use this script to remove all but the latest version.

# e.g.
# 2021-01-01_trip-12345.gpx <- this one is deleted
# 2024-05-05_trip-12345.gpx

use strict;
use warnings;
my %h;
my %fn;

for (sort <*.gpx>)
{
    next unless m/^(\d\d\d\d-\d\d-\d\d).*-(\d+)\.gpx$/;
    my ($d, $id) = ($1, $2);

    if (exists $h{$id})
    {
        print "unlink $id -> $h{$id}: $fn{$id}\n";
        unlink $fn{$id} or die $!;
    }

    $h{$id} = $d;
    $fn{$id} = $_;
}
