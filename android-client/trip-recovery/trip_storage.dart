import 'trip_journal.dart';
import 'trip_storage_web.dart' if (dart.library.io) 'trip_storage_io.dart'
    as platform;

Future<TripStore> openTripStore() => platform.openTripStore();
