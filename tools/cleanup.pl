#!/usr/bin/perl

# Edited tracks are re-downloaded with new date and same id
# so with --add-date you end up with several files.
# Use this script to remove all but the latest version.

# e.g.
# 2021-01-01_trip-12345.gpx <- this one is deleted
# 2024-05-05_trip-12345.gpx

use strict;
use warnings;
use Data::Dumper;
my %h;
my %fn;

my @a = sort <*.gpx>;
for (@a)
{
    next unless m/^(\d\d\d\d-\d\d-\d\d).*-(\d+)\.gpx$/;
    my $d = $1;
    my $id = $2;

    if (!exists $h{$id})
    {
        $h{$id} = $d;
        $fn{$id} = $_;
        next;
    }

    print "unlink $id -> $h{$id}: $fn{$id}\n";
    unlink $fn{$id} or die $!;
    $h{$id} = $d;
    $fn{$id} = $_;
}
