// TPL - medicao curta (Golden Gate) em Java. Mesmo calculo do tpl_curto.py.
// Rode: java TplCurto.java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public class TplCurto {
    // round do Python: arredonda o valor binario exato, empate para o par
    static double roundN(double x, int n) { return new BigDecimal(x).setScale(n, RoundingMode.HALF_EVEN).doubleValue(); }
    static String sn(boolean b) { return b ? "SIM" : "NAO"; }
    public static void main(String[] a) throws Exception {
        int vaoCentral = 1280, vaoLateral = 343, torreAgua = 227, torrePista = 152;
        int pista = torreAgua - torrePista;
        int flecha = torrePista - 6;
        double razao = (double) vaoLateral / vaoCentral;
        double flechaLat = flecha * Math.pow(razao, 2);
        double[] cabo = new double[33];
        for (int i = 0; i < 33; i++) cabo[i] = roundN(torreAgua - 4.0 * flecha * ((double) i / 32) * (1 - (double) i / 32), 3);
        int imin = 0; boolean sim = true;
        for (int i = 1; i < 33; i++) if (cabo[i] < cabo[imin]) imin = i;
        for (int i = 0; i < 33; i++) if (cabo[i] != cabo[32 - i]) sim = false;
        String texto = "{\"cabo_minimo_m\": " + cabo[imin] + ", \"cabo_minimo_no_meio\": \"" + sn(imin == 16) + "\", \"cabo_simetrico\": \"" + sn(sim)
            + "\", \"flecha_central_m\": " + flecha + ", \"flecha_lateral_m\": " + roundN(flechaLat, 3) + ", \"lateral_sobre_central\": " + roundN(razao, 6)
            + ", \"pista_m\": " + pista + "}";
        byte[] d = MessageDigest.getInstance("SHA-256").digest(texto.getBytes(StandardCharsets.UTF_8));
        StringBuilder h = new StringBuilder(); for (byte b : d) h.append(String.format("%02x", b));
        System.out.println(texto);
        System.out.println("resultado_sha256: " + h);
    }
}
