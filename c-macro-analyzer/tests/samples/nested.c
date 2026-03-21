// tests/samples/nested.c
#define PLATFORM "linux"
#define VERSION 3

#ifdef DEBUG
  #if VERSION > 2
    #if defined(FEATURE_X) && !defined(FEATURE_Y)
      // Target line 7
      advanced_feature();
    #endif
  #endif
#endif

#if PLATFORM == "windows"
  windows_specific();
#elif PLATFORM == "linux"
  linux_specific();
#else
  other_platform();
#endif