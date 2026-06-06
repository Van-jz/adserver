import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;

public class HmacSha256Example {

    public static String getAuthenticationId(String reqId, String token) {
        try {
            Mac hmacSha256 = Mac.getInstance("HmacSHA256");
            SecretKeySpec secretKey = new SecretKeySpec(token.getBytes(), "HmacSHA256");
            hmacSha256.init(secretKey);
            byte[] bytes = hmacSha256.doFinal(reqId.getBytes());
            return bytesToHex(bytes);
        } catch (Exception e) {
            throw new RuntimeException("", e);
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }

    // 主函数，用于演示
    public static void main(String[] args) {
        String req = "uniquerequestid2023112911500001";
        String token = "92117e18b6391b92451277e318f36d0c";

        System.out.println(getAuthenticationId(req, token));
        System.out.println(getAuthenticationId("unique-request-id2023112911500001", token));
        System.out.println(getAuthenticationId("9r90wurjqw", "12345asdfg"));
    }
}
