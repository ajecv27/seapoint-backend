// SEAPOINT_VISIBLE_BOAT_V1
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Android's native map projection returns physical pixels; iOS and web use
/// logical coordinates. Keep the boat the same visible size on every phone.
Offset logicalBoatPosition(double x, double y, double density,
        {required bool android}) =>
    Offset(x, y) / (android ? density : 1);

class NavigationBoatMarker extends StatelessWidget {
  const NavigationBoatMarker(
      {super.key, required this.heading, required this.mapBearing});
  final double heading;
  final double mapBearing;
  static const double size = 34;

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Transform.rotate(
          angle: (heading - mapBearing) * math.pi / 180,
          child: const SizedBox(
              width: size,
              height: size,
              child: CustomPaint(painter: _BoatNeedlePainter())),
        ),
      );
}

class _BoatNeedlePainter extends CustomPainter {
  const _BoatNeedlePainter();
  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()
      ..moveTo(size.width / 2, 2)
      ..lineTo(size.width - 3, size.height - 3)
      ..lineTo(size.width / 2, size.height - 10)
      ..lineTo(3, size.height - 3)
      ..close();
    canvas.drawShadow(path, Colors.black87, 3, false);
    canvas.drawPath(
        path,
        Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5
          ..strokeJoin = StrokeJoin.round);
    canvas.drawPath(path, Paint()..color = const Color(0xFF1BA8FF));
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

bool get usesAndroidMapPixels =>
    !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
