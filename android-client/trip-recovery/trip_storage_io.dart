import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'trip_journal.dart';

Future<TripStore> openTripStore() async {
  final support = await getApplicationSupportDirectory();
  return TripStore(FileTripStorage(Directory('${support.path}/trips')));
}

/// Android stores the journal in the app's private support directory. Each GPS
/// record is flushed; the initial file is published by a same-directory rename.
class FileTripStorage implements TripStorage {
  FileTripStorage(this.directory);
  final Directory directory;
  File get _active => File('${directory.path}/active-v1.jsonl');
  File get _completed => File('${directory.path}/last-v1.jsonl');
  File? _readFile;

  @override
  Future<String?> read() async {
    final file = await _active.exists() ? _active : _completed;
    if (!await file.exists()) return null;
    if (await file.length() > TripJournal.maximumBytes) {
      throw const FormatException('Saved trip exceeds storage limit');
    }
    _readFile = file;
    return file.readAsString();
  }

  @override
  Future<void> replace(String record) async {
    await directory.create(recursive: true);
    final stage = File('${directory.path}/active-v1.next');
    await stage.writeAsString(record, flush: true);
    await stage.rename(_active.path);
    _readFile = _active;
  }

  @override
  Future<void> append(String record) async {
    final bytes = utf8.encode(record);
    if (!await _active.exists() ||
        await _active.length() + bytes.length > TripJournal.maximumBytes) {
      throw const FileSystemException('Trip storage unavailable or full');
    }
    final handle = await _active.open(mode: FileMode.append);
    try {
      await handle.writeFrom(bytes);
      await handle.flush();
    } finally {
      await handle.close();
    }
  }

  @override
  Future<void> complete() async {
    await _active.rename(_completed.path);
    _readFile = _completed;
  }

  @override
  Future<void> discard() async {
    final file = _readFile ?? _active;
    if (await file.exists()) await file.delete();
    _readFile = null;
  }
}
