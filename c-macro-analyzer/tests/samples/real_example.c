// tests/samples/real_example.c
#define WASM_ENABLE_REF_TYPES 1
#define WASM_ENABLE_EXTENDED_CONST_EXPR 0
#define WASM_ENABLE_GC 1

#if WASM_ENABLE_GC != 0
  #if WASM_ENABLE_EXTENDED_CONST_EXPR != 0
    #define EXTRA_PARAM NULL
  #else
    #define EXTRA_PARAM
  #endif
  
  void process_gc() {
    // Line 13 - target
    some_function(EXTRA_PARAM);
  }
#endif