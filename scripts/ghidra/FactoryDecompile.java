// Resolve instruction addresses before using the repository's own decompiler.
//@category Factory

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class FactoryDecompile extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException("usage: FactoryDecompile.java OUTPUT ADDRESS...");
        }
        for (int i = 1; i < args.length; i++) {
            Address address = toAddr(args[i]);
            if (address == null) {
                continue; // Keep the original helper's partial-output/error behavior.
            }
            Function function = getFunctionContaining(address);
            if (function != null) {
                args[i] = function.getEntryPoint().toString();
            }
        }
        runScript("DecompileFunctions.java", args);
    }
}
