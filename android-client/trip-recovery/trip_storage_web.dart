import 'package:shared_preferences/shared_preferences.dart';

import 'trip_journal.dart';

Future<TripStore> openTripStore() async =>
    TripStore(_WebTripStorage(await SharedPreferences.getInstance()));

/// Browser compatibility; Android uses the flushed file journal instead.
class _WebTripStorage implements TripStorage {
  _WebTripStorage(this.preferences);
  final SharedPreferences preferences;
  static const active = 'seapoint_active_trip_v1';
  static const completed = 'seapoint_last_trip_v1';
  String? _readKey;

  Future<void> _put(String key, String value) async {
    if (value.length > TripJournal.maximumBytes ||
        !await preferences.setString(key, value)) {
      throw StateError('Trip saving unavailable');
    }
  }

  @override
  Future<String?> read() async {
    _readKey = preferences.containsKey(active) ? active : completed;
    return preferences.getString(_readKey!);
  }

  @override
  Future<void> replace(String record) async {
    await _put(active, record);
    _readKey = active;
  }

  @override
  Future<void> append(String record) async {
    final before = preferences.getString(active);
    if (before == null) throw StateError('No active saved trip');
    await _put(active, before + record);
  }

  @override
  Future<void> complete() async {
    final value = preferences.getString(active);
    if (value == null) throw StateError('No active saved trip');
    await _put(completed, value);
    if (!await preferences.remove(active)) {
      throw StateError('Trip saving unavailable');
    }
    _readKey = completed;
  }

  @override
  Future<void> discard() async {
    if (!await preferences.remove(_readKey ?? active)) {
      throw StateError('Trip saving unavailable');
    }
  }
}
