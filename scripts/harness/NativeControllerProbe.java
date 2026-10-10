package net.runelite.client.input.controller;

import com.google.gson.Gson;
import java.util.*;

/** Poll real SDL hardware without input injection or writing Steam configuration files. */
public final class NativeControllerProbe {
 public static void main(String[] args)throws Exception {
  Map<String,Object> result=new LinkedHashMap<>();
  int connected=0,observedButtons=0;float maxAxis=0;
  try(SdlGamepad controller=new SdlGamepad()) {
   controller.init();GamepadState state=new GamepadState();
   result.put("sdl_initialized",true);
   result.put("joysticks",SdlGamepad.Sdl.SDL_NumJoysticks());
   for(int i=0;i<100;i++) {
    controller.poll(state);
    if(state.connected)connected++;
    observedButtons|=state.buttonsHeld;
    maxAxis=Math.max(maxAxis,Math.max(Math.abs(state.leftX),Math.max(Math.abs(state.leftY),Math.max(Math.abs(state.rightX),Math.abs(state.rightY)))));
    Thread.sleep(50);
   }
   result.put("connected_samples",connected);result.put("total_samples",100);
   result.put("observed_buttons_mask",observedButtons);result.put("maximum_stick_magnitude",maxAxis);
   result.put("note","Real SDL detection/polling only; no physical mapping, gameplay or Gaming Mode acceptance inferred.");
  }
  System.out.println(new Gson().toJson(result));
 }
}
