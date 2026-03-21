// tests/samples/simple.c
#define VERSION 2

#ifdef DEBUG
  // Debug-specific code
  log_message("Debug mode");
#endif

#if VERSION > 1
  // New feature in version 2
  enable_feature();
#else
  // Old version code
  use_legacy();
#endif