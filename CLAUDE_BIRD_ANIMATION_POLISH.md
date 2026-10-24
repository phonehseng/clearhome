# Claude handoff: recognizable birds and natural flight

Implement, visually verify, commit, and push this user-requested improvement to the animated background birds. The user says the current birds look like half-moons scissoring against each other rather than actual flying birds.

- Inspect the current bird shapes, transforms, and animation layers. Replace the crescent-like silhouettes and intersecting/scissoring wing movement with clean, recognizable bird silhouettes: a small coherent body with two attached wings, readable at the actual display size.
- Draw the birds using the project's existing code-native SVG/CSS approach where practical. Make wing motion pivot naturally at the body, with a restrained flap cycle and brief gliding poses. Avoid rotating disconnected curves through each other or using an obvious spinning animation.
- Keep flight paths smooth, with subtle variation in size, speed, spacing, and flap timing so the flock feels natural. Keep the effect quiet enough that it does not compete with the housing tools or obscure text and controls.
- Preserve correct layering, clipping, and pointer-event behavior. Birds should not pop into view mid-screen or disappear behind unintended panels. Avoid excessive animation work and respect prefers-reduced-motion.
- Check every page or background variant that uses these birds so the old broken shapes do not remain in another view.
- Visually inspect the animation in a browser at desktop and mobile widths, including the flap transitions and gliding pose. Confirm the birds remain recognizable at their rendered size, the wings do not scissor through one another, and controls remain usable. A code/syntax check alone is insufficient for this visual request.

Please commit and push the actual visual implementation, then report the commit and checks. This file is only the request, not the bird fix. If already implemented, verify and report the existing implementation commit rather than making an empty commit.
