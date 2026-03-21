// tests/samples/complex.c
#define ARCH "x86_64"
#define OPTIMIZE 1
#define DEBUG_LEVEL 3

#if defined(DEBUG) && DEBUG_LEVEL > 1
  #if ARCH == "x86_64"
    #if OPTIMIZE
      optimized_x86_debug();
    #else
      plain_x86_debug();
    #endif
  #elif ARCH == "arm"
    arm_debug();
  #else
    generic_debug();
  #endif
#endif

#ifndef RELEASE
  development_code();
#endif

#if (PLATFORM == "linux" || PLATFORM == "darwin") && !EMBEDDED
  desktop_feature();
#endif