---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---
Review this custom Drupal 11 module before we merge it. Give me your findings.

`event_feed/event_feed.routing.yml`
```yaml
event_feed.public_feed:
  path: '/events/feed'
  defaults:
    _controller: '\Drupal\event_feed\Controller\EventFeedController::feed'
  requirements:
    _access: 'TRUE'

event_feed.settings:
  path: '/admin/config/event-feed'
  defaults:
    _form: '\Drupal\event_feed\Form\EventFeedSettingsForm'
  requirements:
    _permission: 'administer site configuration'
```

`event_feed/src/Controller/EventFeedController.php`
```php
<?php

namespace Drupal\event_feed\Controller;

use Drupal\Core\Controller\ControllerBase;
use Symfony\Component\HttpFoundation\Request;

class EventFeedController extends ControllerBase {

  public function feed(Request $request) {
    $category = $request->query->get('category');
    $sql = "SELECT nid FROM {node_field_data} WHERE type = 'event' AND title LIKE '%" . $category . "%'";
    $nids = \Drupal::database()->query($sql)->fetchCol();

    $items = [];
    foreach ($this->entityTypeManager()->getStorage('node')->loadMultiple($nids) as $node) {
      $items[] = '<li>' . $node->get('field_summary')->value . '</li>';
    }

    return [
      '#markup' => '<ul>' . implode('', $items) . '</ul>',
    ];
  }

}
```

`event_feed/src/Form/EventFeedSettingsForm.php`
```php
<?php

namespace Drupal\event_feed\Form;

use Drupal\Core\Form\ConfigFormBase;
use Drupal\Core\Form\FormStateInterface;

class EventFeedSettingsForm extends ConfigFormBase {

  protected function getEditableConfigNames() {
    return ['event_feed.settings'];
  }

  public function getFormId() {
    return 'event_feed_settings';
  }

  public function buildForm(array $form, FormStateInterface $form_state) {
    $config = $this->config('event_feed.settings');
    $intro = $config->get('intro_text');

    // Show a count of events in the configured category.
    $tracked = $config->get('tracked_category');
    $count_sql = "SELECT COUNT(*) FROM {node_field_data} WHERE type = 'event' AND title LIKE '%" . $tracked . "%'";
    $count = \Drupal::database()->query($count_sql)->fetchField();

    $form['stats'] = [
      '#markup' => '<p>Tracking ' . $count . ' events.</p>',
    ];
    $form['preview'] = [
      '#markup' => '<div class="intro-preview">' . $intro . '</div>',
    ];
    $form['tracked_category'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Tracked category'),
      '#default_value' => $tracked,
    ];
    $form['intro_text'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Intro text'),
      '#default_value' => $intro,
    ];
    return parent::buildForm($form, $form_state);
  }

  public function submitForm(array &$form, FormStateInterface $form_state) {
    $this->config('event_feed.settings')
      ->set('intro_text', $form_state->getValue('intro_text'))
      ->set('tracked_category', $form_state->getValue('tracked_category'))
      ->save();
    parent::submitForm($form, $form_state);
  }

}
```
