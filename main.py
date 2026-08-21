$data = [
    'api_key'    => 'b25eb076f5c0412fa9f1eba94550d02e',
    'action'     => 'buy',
    'product_id' => 'PID_ID',
    'duration'   => '1 Day'
];

$ch = curl_init('https://adminpanels.shop/api/reseller_v1.php');
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($data));
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/x-www-form-urlencoded']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
curl_close($ch);
echo $response;
