#ifndef HEADER_GUARD_H
#define HEADER_GUARD_H

#define VERSION 2
#define DEBUG

#ifdef DEBUG
  // Debug code
  log_message("Debug");
#endif

#if VERSION > 1
  // New feature
  enable_feature();
#endif

#endif // HEADER_GUARD_H
